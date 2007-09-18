import os
import tempfile
import time

from rpmUtils.miscutils import rpm2cpio

from dims import img
from dims import pps
from dims import sync

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import RepoMixin #!
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
  def _extract(self):
    self.remove_output(all=True)
    
    # generate output files
    try:
      # get input - extract RPMs
      # create temporary directory for rpms, gets deleted once done
      working_dir = P(tempfile.mkdtemp(dir=self.TEMP_DIR))
      
      for rpmname in self._find_rpms():
        self._extract_rpm(rpmname, working_dir)
      
      # need to modify self.data, so that the metadata written has all
      # the files created. Otherwise, self.data['output'] will be
      # empty.
      self.DATA['output'].extend(self._generate(working_dir))
    finally:
      working_dir.rm(recursive=True)
    
    # write metadata
    self.write_metadata()
  
  def _extract_rpm(self, rpmPath, output=P(os.getcwd())):
    """ 
    Extract the contents of the RPM file specified by rpmPath to
    the output location. The rpmPath parameter can use globbing.
  
    @param rpmPath : the path to the RPM file    
    @param output  : the directory that is going to contain the RPM's
                     contents
    """
    # create temporary directory for rpm contents
    dir = P(tempfile.mkdtemp(dir=self.TEMP_DIR))
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
    

class ImageModifyMixin(RepoMixin):
  """ 
  Classes that extend this must require 'anaconda-version' and
  'buildstamp-file.'

  This class downloads (if the image exists) and modifies it.
  """
  def __init__(self, name):
    self.imagedir = self.mddir/'image'
    
    self.name = name 
    self.image = None
    self.i_locals = None
  
  def setup(self):
    self.images_src = self.METADATA_DIR/'images-src'/self.name
    if self.images_src.exists():
      self.DATA['input'].append(self.images_src)
    
    self.setup_diff(self.DATA)
    
    self.setup_sync(self.imagedir,
                    xpaths=['/distro/installer/%s/path' % self.name],
                    id='%s-input-files' % self.name)
  
  def check(self):
    return not self._validate_image or \
           self.test_diffs()
  
  def _register_image_locals(self, locals):
    self.i_locals = locals_imerge(locals, self.cvars['anaconda-version'])
    
    repo = self.getRepo(self.getBaseRepoId())
    
    image_path = self.i_locals.get('//images/image[@id="%s"]/path' % self.name)
    image_path = locals_printf(image_path, self.cvars['base-vars'])
    try:
      self.setup_sync(self.SOFTWARE_STORE/image_path,
                      id='ImageModifyMixin',
                      paths=[repo.rjoin(image_path, self.name)])
    except IOError, e:
      if self._isvirtual():
        self.DATA['output'].append(self.SOFTWARE_STORE/image_path/self.name)
      else:
        raise e
    self.l_image = self.i_locals.get('//images/image[@id="%s"]' % self.name)
  
  def _open(self):
    image  = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    path   = self._getpath()
    format = image.get('format/text()')
    zipped = image.get('zipped/text()', 'False') in BOOLEANS_TRUE
    
    if image.attrib.get('virtual', 'False') in BOOLEANS_TRUE:
      if path.exists(): path.remove() # delete old image
    path.dirname.mkdirs()
    self.image = img.MakeImage(path, format, zipped)
    self.image.open()
  
  def _close(self):
    self.image.close()
    img.cleanup()
  
  def _modify(self):
    # sync image to input store
    self.sync_input(what=['ImageModifyMixin', '%s-input-files' % self.name])
    
    # modify image
    self.log(1, "modifying %s" % self.name)
    self._open()
    self._generate()
    self._close()
    
    # validate output
    if not self._validate_image():
      raise OutputInvalidError("output files are invalid")
    
    # write metadata
    self.write_metadata()
  
  def _generate(self):
    self.cvars['%s-changed' % self.name] = True
    if self.imagedir.exists():
      self._write_directory(self.imagedir)
    if self.images_src.exists():
      self._write_directory(self.images_src)
  
  def _write_buildstamp(self):
    self.image.write(self.cvars['buildstamp-file'], '/')
  
  def _write_directory(self, dir, dest='/'):
    self.image.write([ file for file in dir.listdir() ], dest)
  
  def _getpath(self):
    FILE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return self.SOFTWARE_STORE / \
           locals_printf(FILE.get('path'), self.cvars['base-vars']) / \
           self.name
  
  def _iszipped(self):
    IMAGE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return IMAGE.get('zipped/text()', 'False') in BOOLEANS_TRUE
  
  def _isvirtual(self):
    IMAGE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return IMAGE.get('@virtual', 'True') in BOOLEANS_TRUE
  
  def _validate_image(self):
    p = self._getpath()
    if not p.exists():
      return False
    else:
      if self._iszipped():
        return magic_match(p) == FILE_TYPE_GZIP
      else:
        format = self.l_image.get('format/text()')
        return magic_match(p) == MAGIC_MAP[format]


class FileDownloadMixin(RepoMixin):
  """ 
  Classes that extend this must require 'anaconda-version' and
  'source-vars'.

  This class should be used to download files besides the images.
  """  
  def __init__(self, repoid):
    self.f_locals = None
    
    self.repoid = repoid
    
  def _register_file_locals(self, locals):
    self.f_locals = locals_imerge(locals, self.cvars['anaconda-version'])
    paths = []
    for file in self.f_locals.xpath('//files/file'):
      filename = file.attrib['id']
      if file.attrib.get('virtual', 'False') in BOOLEANS_TRUE:
        continue # skip virtual files      
      
      rinfix = locals_printf(file.get('path'), self.cvars['source-vars'])
      linfix = locals_printf(file.get('path'), self.cvars['base-vars'])
      self.setup_sync(
        self.SOFTWARE_STORE/linfix, id='FileDownloadMixin',
        paths=[self.getRepo(self.repoid).rjoin(rinfix, filename)])
  
  def _download(self):
    self.sync_input(what='FileDownloadMixin')
    
class RpmNotFoundError(Exception): pass
class OutputInvalidError(Exception): pass
