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

from dimsbuild.modules.lib import DiffMixin, FilesMixin

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')

MAGIC_MAP = {
  'ext2': FILE_TYPE_EXT2FS,
  'cpio': FILE_TYPE_CPIO,
  'squashfs': FILE_TYPE_SQUASHFS,
  'fat32': FILE_TYPE_FAT,
}


#------ HELPER FUNCTIONS ------#
def extractRpm(rpmPath, output=os.getcwd()):
  """ 
  Extract the contents of the RPM file specified by rpmPath to
  the output location. The rpmPath parameter can use globbing.
  
  @param rpmPath : the path to the RPM file    
  @param output  : the directory that is going to contain the RPM's
  contents
  """
  dir = tempfile.mkdtemp(dir='/tmp/dimsbuild')
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


class ExtractHandler(DiffMixin):
  def __init__(self, interface, data, mdfile):    
    self.interface = interface
    self.config = self.interface.config
    self.software_store = self.interface.SOFTWARE_STORE
    
    DiffMixin.__init__(self, mdfile, data)

  def setup(self):
    self.update({
      'input':  self.find_rpms(),
      'output': self.handlers['output'].oldoutput.keys(),
    })

  def clean(self):
    self.clean_output()
    self.clean_metadata()
    
  def check(self):    
    return self.test_diffs()
  
  def extract(self, message):
    self.interface.log(0, message)
    self.clean_output()
    
    # generate output files
    try:
      # get input - extract RPMs
      working_dir = tempfile.mkdtemp(dir='/tmp/dimsbuild') # temporary directory, gets deleted once done

      for rpmname in self.find_rpms():
        extractRpm(rpmname, working_dir)
      
      # need to modify self.data, so that the metadata written has all
      # the files created. Otherwise, self.data['output'] will be
      # empty.
      self.update({'output': self.generate(working_dir)})
    finally:
      osutils.rm(working_dir, recursive=True, force=True)

    # write metadata
    self.write_metadata()

  def clean_output(self):
    if self.handlers.has_key('output'):      
      for file in self.handlers['output'].oldoutput.keys():
        osutils.rm(file, recursive=True, force=True)
    while len(self.handlers['output'].data) > 0:
      self.handlers['output'].data.pop()
        
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


class ImageModifyMixin(ImageHandler, DiffMixin, FilesMixin):
  """
  Classes that extend this must require 'anaconda-version' and
  'buildstamp-file.'  
  """
  def __init__(self, name, interface, data, mdfile=None):
    if mdfile is None:
      self.mdfile = join(interface.METADATA_DIR, '%s.md' % name)
    else:
      self.mdfile = mdfile

    ImageHandler.__init__(self, interface)
    DiffMixin.__init__(self, self.mdfile, data)
    FilesMixin.__init__(self, '/')

    self.name = name        

  def setup(self, config=True):
    if config:
      self.add_files(xpaths='/distro/installer/%s/path' % self.name,
                     addoutput=False)

    imagessrc = join(self.interface.METADATA_DIR, 'images-src', self.name)
    if exists(imagessrc):
      self.update({
        'input': imagessrc,
      })
    
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
    self.write_metadata()
  
  def generate(self):
    self.interface.cvars['%s-changed' % self.name] = True
    self.sync_files(action=self.write_file)                    
    
  def write_file(self, src, dest):
    self.image.write(src, dest)

  def remove_files(self, rmlist=[]):
    for item in rmlist:
      if exists(item):
        self.interface.log(2, "removing %s" % osutils.basename(item))
        osutils.rm(item, recursive=True, force=True)

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
