import os
import tempfile
import time

from rpmUtils.miscutils import rpm2cpio

from dims import img
from dims import pps
from dims import sync

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.logging   import L1
from dimsbuild.magic     import (FILE_TYPE_GZIP, FILE_TYPE_EXT2FS,
                                 FILE_TYPE_CPIO, FILE_TYPE_SQUASHFS,
                                 FILE_TYPE_FAT, match as magic_match)

__all__ = ['ExtractMixin', 'ImageModifyMixin', 'FileDownloadMixin',
           'RpmNotFoundError', 'OutputInvalidError']

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


class ImageModifyMixin:
  """
  Classes that extend this must require 'anaconda-version',
  'buildstamp-file' and 'base-repoid'.

  This class downloads (if the image exists) and modifies it.
  """
  def __init__(self, name):
    self.imagedir = self.mddir/'image'

    self.name = name
    self.image = None
    self.image_locals = None # this must be set before setup() is called

    # dictionary of dest, sourcelist pairs for files to be placed inside
    # the image
    self.cvars['%s-content' % self.id] = {}

  def setup(self):
    # input images
    repo = self.cvars['repos'][self.cvars['base-repoid']]

    image_path = self.image_locals['path'] % self.cvars['base-vars']

    self.diff.setup(self.DATA)

    try:
      self.io.setup_sync((self.SOFTWARE_STORE/image_path).dirname,
                         id='ImageModifyMixin',
                         paths=[repo.osdir/image_path])
    except IOError:
      if self.virtual:
        self.DATA['output'].append(self.SOFTWARE_STORE/image_path)
      else:
        raise

    # other image input files
    for dst, src in self.cvars['%s-content' % self.id].items():
      self.io.setup_sync(self.imagedir/dst.lstrip('/'),
                         paths=src,
                         id='%s-input-files' % self.name)

    self.io.setup_sync(self.imagedir,
                       xpaths=['path'],
                       id='%s-input-files' % self.name)

  def check(self):
    return self.diff.test_diffs()

  def apply(self):
    self.io.clean_eventcache()

  def verify_output_exists(self):
    "verify all output exists"
    for file in self.io.list_output():
      self.verifier.failUnless(file.exists(), "unabled to find file '%s" % file)

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
    self.io.sync_input(what=['ImageModifyMixin', '%s-input-files' % self.name], cache=True)

    # modify image
    self.log(1, L1("modifying %s" % self.name))
    self._open()
    self._generate()
    self._close()

    # write metadata
    self.diff.write_metadata()

  def _generate(self):
    if self.imagedir.exists():
      self._write_directory(self.imagedir)

  def _write_buildstamp(self):
    self.image.write(self.cvars['buildstamp-file'], '/')

  def _write_directory(self, dir, dest='/'):
    self.image.write([ file for file in dir.listdir() ], dest)

  path    = property(lambda self: self.SOFTWARE_STORE / \
                                  self.image_locals['path'] % \
                                  self.cvars['base-vars'])
  zipped  = property(lambda self: self.image_locals.get('zipped', False))
  virtual = property(lambda self: self.image_locals.get('virtual', False))

  def verify_image(self):
    "verify image existence."
    self.verifier.failUnless(self.path.exists(), "'%s' does not exist" % self.path)
    if self.zipped:
      self.verifier.failUnless(magic_match(self.path) == FILE_TYPE_GZIP,
                      "expected gzipped image file")
    else:
      self.verifier.failUnless(magic_match(self.path) == MAGIC_MAP[self.image_locals['format']],
                      "expected %s image format" % self.image_locals['format'])


class FileDownloadMixin:
  """
  Classes that extend this must require 'anaconda-version',
  'source-vars' and 'base-repoid'.

  This class should be used to download files besides the images.
  """
  def __init__(self):
    self.file_locals = None

  def setup(self):
    paths = []
    for data in self.file_locals.values():
      if data.get('virtual', False): continue # skip virtual files

      rinfix = data['path'] % self.cvars['source-vars']
      linfix = data['path'] % self.cvars['base-vars']
      self.io.setup_sync(
        (self.SOFTWARE_STORE/linfix).dirname, id='FileDownloadMixin',
        paths=[self.cvars['repos'][self.cvars['base-repoid']].osdir/rinfix])

  def apply(self):
    self.io.clean_eventcache()

  def verify_output_exists(self):
    "verify all output exists"
    for file in self.io.list_output():
      self.verifier.failUnless(file.exists(), "unabled to find file '%s" % file)

  def _download(self):
    self.io.sync_input(what='FileDownloadMixin', cache=True)

class RpmNotFoundError(Exception): pass
class OutputInvalidError(Exception): pass
