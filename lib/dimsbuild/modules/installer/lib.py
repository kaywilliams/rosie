import os
import tempfile
import time

from StringIO import StringIO
from os.path  import exists, isdir, join
from rpmUtils.miscutils import rpm2cpio

from dims import FormattedFile as ffile
from dims import imerge
from dims import img
from dims import osutils
from dims import sync
from dims import xmltree

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.locals    import L_BUILDSTAMP_FORMAT, L_IMAGES
from dimsbuild.magic     import match as magic_match
from dimsbuild.magic     import FILE_TYPE_GZIP, FILE_TYPE_EXT2FS, FILE_TYPE_CPIO, FILE_TYPE_SQUASHFS, FILE_TYPE_FAT
from dimsbuild.misc      import locals_imerge, locals_printf

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')

MAGIC_MAP = {
  'ext2': FILE_TYPE_EXT2FS,
  'cpio': FILE_TYPE_CPIO,
  'squashfs': FILE_TYPE_SQUASHFS,
  'fat32': FILE_TYPE_FAT,
}

class ExtractHandler:
  def __init__(self, interface, data, mdfile):    
    self.interface = interface
    self.config = self.interface.config
    self.software_store = self.interface.SOFTWARE_STORE

    self.DATA = data
    self.mdfile = mdfile
    
  def setup(self):
    self.DATA['input'].extend(self.find_rpms())
    self.interface.setup_diff(self.mdfile, self.DATA)

  def clean(self):
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
    
  def check(self):
    return self.interface.test_diffs()
  
  def extract(self, message):
    self.interface.log(0, message)
    self.interface.remove_output(all=True)
    
    # generate output files
    try:
      # get input - extract RPMs
      # create temporary directory for rpms, gets deleted once done
      working_dir = tempfile.mkdtemp(dir=self.interface.TEMP_DIR) 

      for rpmname in self.find_rpms():
        self.extractRpm(rpmname, working_dir)
      
      # need to modify self.data, so that the metadata written has all
      # the files created. Otherwise, self.data['output'] will be
      # empty.
      self.DATA['output'].extend(self.generate(working_dir))
    finally:
      osutils.rm(working_dir, recursive=True, force=True)

    # write metadata
    self.interface.write_metadata()

  def extractRpm(self, rpmPath, output=os.getcwd()):
    """ 
    Extract the contents of the RPM file specified by rpmPath to
    the output location. The rpmPath parameter can use globbing.
  
    @param rpmPath : the path to the RPM file    
    @param output  : the directory that is going to contain the RPM's
    contents
    """
    # create temporary directory for rpm contents
    dir = tempfile.mkdtemp(dir=self.interface.TEMP_DIR)
    try:
      filename = join(dir, 'rpm.cpio')
    
      # sync the RPM down to the temporary directory
      sync.sync(rpmPath, dir)
      rpmFile = join(dir, osutils.basename(rpmPath))
    
      rpm2cpio(os.open(rpmFile, os.O_RDONLY), open(filename, 'w+'))
      cpio = img.MakeImage(filename, 'cpio')
      if not exists(output):
        osutils.mkdir(output, parent=True)    
      cpio.open(point=output)
    finally:
      osutils.rm(dir, recursive=True, force=True)
        
class ImageHandler:
  """
  Classes that extend this must require 'anaconda-version',
  'buildstamp-file.'
  """
  def __init__(self, interface):
    self.name = 'super' # subclasses override this
    self.image = None
    self.interface = interface
    self.i_locals = None
    
    self.vars = self.interface.BASE_VARS
    self.anaconda_version = None
  
  def register_image_locals(self, locals):
    self.i_locals = locals_imerge(locals, self.interface.cvars['anaconda-version'])
    self.anaconda_version = self.interface.cvars['anaconda-version']
  
  def open(self):
    image  = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    path   = self._getpath()
    format = image.get('format/text()')
    zipped = image.get('zipped/text()', 'False') in BOOLEANS_TRUE
    
    if image.attrib.get('virtual', 'False') in BOOLEANS_TRUE:
      if exists(path): osutils.rm(path) # delete old image
    self.image = img.MakeImage(path, format, zipped)
    self.image.open()
  
  def close(self):
    self.image.close()
    img.cleanup()
  
  def generate(self):
    raise NotImplementedError
  
  def write_buildstamp(self):
    self.image.write(self.interface.cvars['buildstamp-file'], '/')
  
  def write_directory(self, dir, dest='/'):
    self.image.write([ join(dir, file) for file in os.listdir(dir) ], dest)
  
  def _getpath(self):
    FILE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return join(self.interface.SOFTWARE_STORE,
                locals_printf(FILE.get('path'), self.vars),
                self.name)
  
  def _iszipped(self):
    IMAGE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return IMAGE.get('zipped/text()', 'False') in BOOLEANS_TRUE
  
  def _isvirtual(self):
    IMAGE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return IMAGE.get('@virtual', 'True') in BOOLEANS_TRUE
  
  def validate_image(self):
    p = self._getpath()
    if not exists(p):
      return False
    else:
      if self._iszipped():
        return magic_match(p) == FILE_TYPE_GZIP
      else:
        format = self.l_image.get('format/text()')
        return magic_match(p) == MAGIC_MAP[format]


class ImageModifyMixin(ImageHandler):
  """
  Classes that extend this must require 'anaconda-version' and
  'buildstamp-file.'  
  """
  def __init__(self, name, interface, data, mdfile=None):
    if mdfile is None:
      self.mdfile = join(interface.METADATA_DIR, '%s.md' % name)
    else:
      self.mdfile = mdfile
    self.DATA = data    
    ImageHandler.__init__(self, interface)
    
    self.name = name        

  def setup(self, config=True):
    imagessrc = join(self.interface.METADATA_DIR, 'images-src', self.name)
    if exists(imagessrc):
      self.DATA['input'].append(imagessrc)
    self.interface.setup_diff(self.mdfile, self.DATA)
    if config:
      i,_ = self.interface.setup_sync(xpaths=[(
        '/distro/installer/%s/path' % self.name,
        osutils.dirname(self.interface.config.file),
        '/'
      )])
      self.DATA['input'].extend(i)
    
  def register_image_locals(self, locals):
    ImageHandler.register_image_locals(self, locals)
    
    repo = self.interface.getRepo(self.interface.getBaseRepoId())
    
    image_path = self.i_locals.get('//images/image[@id="%s"]/path' % self.name)
    image_path = locals_printf(image_path, self.interface.BASE_VARS)
    
    self.src = repo.rjoin(image_path, self.name)
    self.username = repo.username
    self.password = repo.password
    self.dest = join(self.interface.SOFTWARE_STORE, image_path, self.name)
    
    self.l_image = self.i_locals.get('//images/image[@id="%s"]' % self.name)
  
  def modify(self):
    # sync image to input store
    try:
      self.interface.cache(self.src, osutils.dirname(self.dest))
    except sync.util.SyncError, e:
      if self._isvirtual(): pass
      else: raise e
      
    # modify image
    self.interface.log(1, "modifying %s" % self.name)
    self.open()
    self.generate()
    self.close()
    
    # validate output
    if not self.validate_image():
      raise OutputInvalidError, "output files are invalid"
    
    # write metadata
    self.interface.write_metadata()
  
  def generate(self):
    self.interface.cvars['%s-changed' % self.name] = True
    self.interface.sync_input(action=self.write_file)
    
  def write_file(self, src, dest):
    self.image.write(src, dest)

class FileDownloadMixin:
  "Classes that extend this must require 'anaconda-version' and 'source-vars'"
  def __init__(self, interface, repoid):
    self.f_locals = None
    
    self.interface = interface
    self.repoid = repoid
    
  def register_file_locals(self, locals):
    self.f_locals = locals_imerge(locals, self.interface.cvars['anaconda-version'])
  
  def download(self):
    if not self.f_locals:
      raise RuntimeError, "FileDownloadMixin instance has no registered locals"
    
    for file in self.f_locals.xpath('//files/file'):
      filename = file.attrib['id']
      if file.attrib.get('virtual', 'False') in BOOLEANS_TRUE: continue # skip virtual files
      
      rinfix = locals_printf(file.get('path'), self.interface.cvars['source-vars'])
      linfix = locals_printf(file.get('path'), self.interface.BASE_VARS)
      
      self.interface.cache(self.interface.getRepo(self.repoid).rjoin(rinfix, filename),
                           join(self.interface.SOFTWARE_STORE, linfix))

class RpmNotFoundError(Exception): pass
class OutputInvalidError(Exception): pass
