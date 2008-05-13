#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
import os
import tempfile
import time

from rpmUtils.miscutils import rpm2cpio

from rendition import img
from rendition import magic
from rendition import pps
from rendition import sync

from spin.constants import BOOLEANS_TRUE
from spin.logging   import L1

__all__ = ['ExtractMixin', 'ImageModifyMixin', 'FileDownloadMixin',
           'RpmNotFoundError', 'OutputInvalidError']

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')

MAGIC_MAP = {
  'ext2':     magic.FILE_TYPE_EXT2FS,
  'cpio':     magic.FILE_TYPE_CPIO,
  'squashfs': magic.FILE_TYPE_SQUASHFS,
  'fat32':    magic.FILE_TYPE_FAT,
}

class ExtractMixin:
  def _extract(self):
    self.io.clean_eventcache(all=True)

    # get input - extract RPMs
    # create temporary directory for rpms, gets deleted once done
    working_dir = pps.path(tempfile.mkdtemp(dir=self.TEMP_DIR))

    # generate output files
    try:
      for rpmname in self._find_rpms():
        self._extract_rpm(rpmname, working_dir)

      # need to modify self.data, so that the metadata written has all
      # the files created. Otherwise, self.data['output'] will be
      # empty.
      self.DATA['output'].extend(self._generate(working_dir))
    finally:
      working_dir.rm(recursive=True)

  def _extract_rpm(self, rpmPath, output=pps.path(os.getcwd())):
    """
    Extract the contents of the RPM file specified by rpmPath to
    the output location. The rpmPath parameter can use globbing.

    @param rpmPath : the path to the RPM file
    @param output  : the directory that is going to contain the RPM's
                     contents
    """
    # create temporary directory for rpm contents
    dir = pps.path(tempfile.mkdtemp(dir=self.TEMP_DIR))
    try:
      filename = dir/'rpm.cpio'

      # sync the RPM down to the temporary directory
      sync.sync(rpmPath, dir) #! fix me (dont use sync)
      rpmFile = dir/rpmPath.basename

      rpm2cpio(os.open(rpmFile, os.O_RDONLY), filename.open('w+'))
      cpio = img.MakeImage(filename, 'cpio')
      if not output.exists():
        output.mkdirs()
      cpio.open(point=output)
    finally:
      dir.rm(recursive=True)


class ImageModifyMixin:
  "This class downloads and modifies images"
  # Classes that extend this must require 'anaconda-version',
  # 'buildstamp-file' and 'installer-repo'.
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
    repo = self.cvars['installer-repo']

    image_path = self.image_locals['path'] % self.cvars['distro-info']

    self.diff.setup(self.DATA)

    try:
      self.io.add_fpath(repo.url/image_path,
                        (self.SOFTWARE_STORE/image_path).dirname,
                        id='ImageModifyMixin')
    except IOError:
      if self.virtual:
        self.DATA['output'].append(self.SOFTWARE_STORE/image_path)
      else:
        raise

    # other image input files
    for dst, src in self.cvars['%s-content' % self.id].items():
      self.io.add_fpaths(src, self.imagedir//dst, id='%s-input-files' % self.name)
    self.io.add_xpath('path', self.imagedir, id='%s-input-files' % self.name)

  def check(self):
    return self.diff.test_diffs()

  def apply(self):
    self.io.clean_eventcache()

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
    # remove current image
    if self.path.exists(): self.path.remove()

    # clean up former output files
    toclean = set(self.mddir.findpaths(type=pps.constants.TYPE_NOT_DIR)).difference(
                  self.io.list_output())
    toclean = set([ x for x in toclean if x.startswith(self.imagedir) ])
    for file in toclean:
      file.remove()
      file.dirname.removedirs()

    # sync image to input store
    self.io.sync_input(what=['ImageModifyMixin', '%s-input-files' % self.name], cache=True)

    # modify image
    self.log(1, L1("modifying %s" % self.name))
    self._open()
    self._generate()
    self._close()

  def _generate(self):
    if self.imagedir.exists():
      self._write_directory(self.imagedir)

  def _write_buildstamp(self):
    self.image.write(self.cvars['buildstamp-file'], '/')

  def _write_directory(self, dir, dest='/'):
    self.image.write([ file for file in dir.listdir() ], dest)

  path    = property(lambda self: ( self.SOFTWARE_STORE /
                                    self.image_locals['path'] %
                                    self.cvars['distro-info']) )
  zipped  = property(lambda self: self.image_locals.get('zipped', False))
  virtual = property(lambda self: self.image_locals.get('virtual', False))

  def verify_image(self):
    "verify image existence."
    self.verifier.failUnlessExists(self.path)
    if self.zipped:
      self.verifier.failUnless(magic.match(self.path) == magic.FILE_TYPE_GZIP,
                               "expected gzipped image file")
    else:
      self.verifier.failUnless(magic.match(self.path) == MAGIC_MAP[self.image_locals['format']],
                               "expected %s image format" % self.image_locals['format'])


class FileDownloadMixin:
  "This class downloads files to a directory of your chosing"
  # Classes that extend this must require 'anaconda-version',
  # 'base-info' and 'installer-repo'.
  def __init__(self):
    self.file_locals = None

  def setup(self):
    paths = []
    for data in self.file_locals.values():
      if data.get('virtual', False): continue # skip virtual files

      rinfix = data['path'] % self.cvars['base-info']
      linfix = data['path'] % self.cvars['distro-info']
      self.io.add_fpath(self.cvars['installer-repo'].url/rinfix,
                        (self.SOFTWARE_STORE/linfix).dirname,
                        id='FileDownloadMixin')

  def apply(self):
    self.io.clean_eventcache()

  def _download(self):
    self.io.sync_input(what='FileDownloadMixin', cache=True)

class RpmNotFoundError(Exception): pass
class OutputInvalidError(Exception): pass
