import os
import tempfile
import time

from rpmUtils.miscutils import rpm2cpio

from dims import img
from dims import pps
from dims import sync

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.magic     import match as magic_match
from dimsbuild.magic     import FILE_TYPE_GZIP, FILE_TYPE_EXT2FS, FILE_TYPE_CPIO, FILE_TYPE_SQUASHFS, FILE_TYPE_FAT
from dimsbuild.misc      import locals_imerge, locals_printf

P = pps.Path

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')

MAGIC_MAP = {
  'ext2': FILE_TYPE_EXT2FS,
  'cpio': FILE_TYPE_CPIO,
  'squashfs': FILE_TYPE_SQUASHFS,
  'fat32': FILE_TYPE_FAT,
}

class ExtractMixin:
  def __init__(self, interface, data, mdfile):    
    self.interface = interface
    self.config = self.interface.config
    self.software_store = self.interface.SOFTWARE_STORE

    self.DATA = data
    self.mdfile = mdfile
    
  def extract(self):
    self.interface.remove_output(all=True)
    
    # generate output files
    try:
      # get input - extract RPMs
      # create temporary directory for rpms, gets deleted once done
      working_dir = P(tempfile.mkdtemp(dir=self.interface.TEMP_DIR))
      
      for rpmname in self.find_rpms():
        self.extract_rpm(rpmname, working_dir)
      
      # need to modify self.data, so that the metadata written has all
      # the files created. Otherwise, self.data['output'] will be
      # empty.
      self.DATA['output'].extend(self.generate(working_dir))
    finally:
      working_dir.rm(recursive=True)
    
    # write metadata
    self.interface.write_metadata()
  
  def extract_rpm(self, rpmPath, output=P(os.getcwd())):
    """ 
    Extract the contents of the RPM file specified by rpmPath to
    the output location. The rpmPath parameter can use globbing.
  
    @param rpmPath : the path to the RPM file    
    @param output  : the directory that is going to contain the RPM's
                     contents
    """
    # create temporary directory for rpm contents
    dir = P(tempfile.mkdtemp(dir=self.interface.TEMP_DIR))
    try:
      filename = dir/'rpm.cpio'
    
      # sync the RPM down to the temporary directory
      sync.sync(rpmPath, dir) #! fix me
      rpmFile = dir/rpmPath.basename
    
      rpm2cpio(os.open(rpmFile, os.O_RDONLY), filename.open('w+'))
      cpio = img.MakeImage(filename, 'cpio')
      if not output.exists():
        output.mkdirs()
      cpio.open(point=output)
    finally:
      dir.rm(recursive=True)
    
class ImageHandler:
  """
  Classes that extend this must require 'anaconda-version',
  'buildstamp-file.'
  """
  def __init__(self, interface, name):
    self.name = name 
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
      if path.exists(): path.remove() # delete old image
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
    self.image.write([ file for file in dir.listdir() ], dest)
  
  def _getpath(self):
    FILE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return self.interface.SOFTWARE_STORE / \
                locals_printf(FILE.get('path'), self.vars) / \
                self.name
  
  def _iszipped(self):
    IMAGE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return IMAGE.get('zipped/text()', 'False') in BOOLEANS_TRUE
  
  def _isvirtual(self):
    IMAGE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return IMAGE.get('@virtual', 'True') in BOOLEANS_TRUE
  
  def validate_image(self):
    p = self._getpath()
    if not p.exists():
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

  This class downloads (if the image exists) and modifies it.
  """
  def __init__(self, name, interface, data, mdfile=None):
    ImageHandler.__init__(self, interface, name)
    self.mdfile = P(mdfile or interface.METADATA_DIR/'INSTALLER'/('%s.md' % name))
    self.DATA = data    
    self.imagedir = self.interface.METADATA_DIR/'INSTALLER'/self.name

  def setup(self):
    imagessrc = self.interface.METADATA_DIR/'images-src'/self.name
    if imagessrc.exists():
      self.DATA['input'].append(imagessrc)
    
    self.interface.setup_diff(self.mdfile, self.DATA)
    
    o = self.interface.setup_sync(xpaths=[('/distro/installer/%s/path' % self.name,
                                           self.imagedir)])
    self.DATA['output'].extend(o)
    
  def register_image_locals(self, locals):
    ImageHandler.register_image_locals(self, locals)
    
    repo = self.interface.getRepo(self.interface.getBaseRepoId())
    
    image_path = self.i_locals.get('//images/image[@id="%s"]/path' % self.name)
    image_path = locals_printf(image_path, self.interface.BASE_VARS)
    try:
      o = self.interface.setup_sync(paths=[(repo.rjoin(image_path, self.name),
                                            self.interface.SOFTWARE_STORE/image_path)],
                                    id='ImageModifyMixin')
      self.DATA['output'].extend(o)
    except IOError:
      if self._isvirtual():
        self.DATA['output'].append(self.interface.SOFTWARE_STORE/image_path/self.name)
      else:
        raise
    self.l_image = self.i_locals.get('//images/image[@id="%s"]' % self.name)
  
  def modify(self):
    # sync image to input store
    self.interface.sync_input(what=['ImageModifyMixin',
                                    '/distro/installer/%s/path' % self.name])
    
    # modify image
    self.interface.log(1, "modifying %s" % self.name)
    self.open()
    self.generate()
    self.close()
    
    # validate output
    if not self.validate_image():
      raise OutputInvalidError("output files are invalid")
    
    # write metadata
    self.interface.write_metadata()
  
  def generate(self):
    self.interface.cvars['%s-changed' % self.name] = True
    if self.imagedir.exists():
      self.write_directory(self.imagedir)

class FileDownloadMixin:
  """ 
  Classes that extend this must require 'anaconda-version' and
  'source-vars'.

  This class should be used to download files besides the images.
  """  
  def __init__(self, interface, repoid):
    self.f_locals = None
    
    self.interface = interface
    self.repoid = repoid
    
  def register_file_locals(self, locals):
    self.f_locals = locals_imerge(locals, self.interface.cvars['anaconda-version'])
    paths = []
    for file in self.f_locals.xpath('//files/file'):
      filename = file.attrib['id']
      if file.attrib.get('virtual', 'False') in BOOLEANS_TRUE:
        continue # skip virtual files      
      
      rinfix = locals_printf(file.get('path'), self.interface.cvars['source-vars'])
      linfix = locals_printf(file.get('path'), self.interface.BASE_VARS)
      paths.append((self.interface.getRepo(self.repoid).rjoin(rinfix, filename),
                    self.interface.SOFTWARE_STORE/linfix))

    o = self.interface.setup_sync(paths=paths, id='FileDownloadMixin')
    self.DATA['output'].extend(o)    

  def download(self):
    self.interface.sync_input(what='FileDownloadMixin')
    
class RpmNotFoundError(Exception): pass
class OutputInvalidError(Exception): pass
