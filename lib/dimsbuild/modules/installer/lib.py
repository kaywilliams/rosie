import os
import tempfile
import time

from rpmUtils.miscutils import rpm2cpio

from dims import img
from dims import pps
from dims import sync

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import RepoMixin #!
from dimsbuild.logging   import L1
from dimsbuild.magic     import (FILE_TYPE_GZIP, FILE_TYPE_EXT2FS,
                                 FILE_TYPE_CPIO, FILE_TYPE_SQUASHFS,
                                 FILE_TYPE_FAT, match as magic_match)

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
    self.io.clean_eventcache(all=True)
    
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
    self.diff.write_metadata()
  
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
    self.image_locals = None # this must be set before setup() is called
  
  def setup(self):
    # input images
    repo = self.getRepo(self.getBaseRepoId())
    
    image_path = self.image_locals['path'] % self.cvars['base-vars']
    try:
      self.io.setup_sync((self.SOFTWARE_STORE/image_path).dirname,
                      id='ImageModifyMixin',
                      paths=[repo.rjoin(image_path)])
    except IOError, e:
      if self.virtual:
        self.DATA['output'].append(self.SOFTWARE_STORE/image_path)
      else:
        raise e
    
    # other image input files
    self.images_src = self.METADATA_DIR/'images-src'/self.name
    if self.images_src.exists():
      self.DATA['input'].append(self.images_src)
    
    self.diff.setup(self.DATA)
    
    self.io.setup_sync(self.imagedir,
                    xpaths=['/distro/installer/%s/path' % self.id],
                    id='%s-input-files' % self.name)
    
  def check(self):
    return not self._validate_image or \
           self.diff.test_diffs()
  
  def _open(self):
    if self.virtual:
      if self.path.exists(): self.path.remove() # delete old image
    self.path.dirname.mkdirs()
    self.image = img.MakeImage(self.path, self.image_locals['format'], self.zipped)
    self.image.open()
  
  def _close(self):
    self.image.close()
    img.cleanup()
  
  def _modify(self):
    # sync image to input store
    self.io.sync_input(what=['ImageModifyMixin', '%s-input-files' % self.name])
    
    # modify image
    self.log(1, L1("modifying %s" % self.name))
    self._open()
    self._generate()
    self._close()
    
    # validate output
    if not self._validate_image():
      raise OutputInvalidError("output files are invalid")
    
    # write metadata
    self.diff.write_metadata()
  
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
  
  path    = property(lambda self: self.SOFTWARE_STORE / \
                                  self.image_locals['path'] % \
                                  self.cvars['base-vars'])
  zipped  = property(lambda self: self.image_locals.get('zipped', False))
  virtual = property(lambda self: self.image_locals.get('virtual', False))
  
  def _validate_image(self):
    if not self.path.exists():
      return False
    else:
      if self.zipped:
        return magic_match(self.path) == FILE_TYPE_GZIP
      else:
        return magic_match(self.path) == MAGIC_MAP[self.image_locals['format']]


class FileDownloadMixin(RepoMixin):
  """ 
  Classes that extend this must require 'anaconda-version' and
  'source-vars'.

  This class should be used to download files besides the images.
  """  
  def __init__(self, repoid):
    self.file_locals = None
    
    self.repoid = repoid
  
  def setup(self):
    paths = []
    for data in self.file_locals.values():
      if data.get('virtual', False): continue # skip virtual files      
      
      rinfix = data['path'] % self.cvars['source-vars']
      linfix = data['path'] % self.cvars['base-vars']
      self.io.setup_sync(
        (self.SOFTWARE_STORE/linfix).dirname, id='FileDownloadMixin',
        paths=[self.getRepo(self.repoid).rjoin(rinfix)])
  
  def _download(self):
    self.io.sync_input(what='FileDownloadMixin')
    
class RpmNotFoundError(Exception): pass
class OutputInvalidError(Exception): pass
