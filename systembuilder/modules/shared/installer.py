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
import time

from rendition import img
from rendition import magic
from rendition import pps

from systembuilder.logging      import L1
from systembuilder.event.fileio import MissingInputFileError

__all__ = ['ImageModifyMixin', 'FileDownloadMixin']

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')

class ImageModifyMixin:
  "This class downloads and modifies images"
  # Classes that extend this must require 'anaconda-version',
  # 'installer-repo', and 'buildstamp-file'
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
    image_path = self.image_locals['path'] % self.cvars['distribution-info']

    self.diff.setup(self.DATA)

    # other image input files
    for dst, src in self.cvars['%s-content' % self.id].items():
      self.io.add_fpaths(src, self.imagedir//dst, id='%s-input-files' % self.name)
    self.io.add_xpath('files', self.imagedir, id='%s-input-files' % self.name)

  def _add_image(self):
    ip = ( self.cvars['installer-repo'].url /
           self.image_locals['path'] % self.cvars['distribution-info'] )
    # check the image format before adding it; if it doesn't match what we're
    # expecting (such as a 404 HTML page), skip it
    try:
      if self.image_locals.get('zipped', False):
        expected = magic.FILE_TYPE_GZIP
      else:
        expected = self.image_locals['format']
      got = magic.match(ip)
      if expected != got:
        raise InvalidImageFormatError(self.image_locals['path'], expected, got)
    except (IOError, pps.Path.error.PathError): # file not found, usually
      pass
    self.io.add_fpath(ip, self.path.dirname, id='ImageModifyMixin')
  def _create_image(self):
    self.DATA['output'].append(self.path)

  def add_image(self):
    self._add_image()
  def add_or_create_image(self):
    try:
      self._add_image()
    except (MissingInputFileError, InvalidImageFormatError):
      self._create_image()
  def create_image(self):
    self._create_image()

  def check(self):
    return self.diff.test_diffs()

  def apply(self):
    self.io.clean_eventcache()

  def _open(self):
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
    self.imagedir.rm(recursive=True, force=True)
    self.imagedir.mkdirs()

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

  def _write_directory(self, dir, dst='/'):
    self.image.write([ f for f in dir.listdir() ], dst)

  path    = property(lambda self: ( self.SOFTWARE_STORE /
                                    self.image_locals['path'] %
                                    self.cvars['distribution-info']) )
  zipped  = property(lambda self: self.image_locals.get('zipped', False))

  def verify_image(self):
    "verify image existence."
    self.verifier.failUnlessExists(self.path)
    if self.zipped:
      self.verifier.failUnless(magic.match(self.path) == magic.FILE_TYPE_GZIP,
                               "expected gzipped image file")
    else:
      self.verifier.failUnless(magic.match(self.path) == self.image_locals['format'],
                               "expected %s image format" % self.image_locals['format'])


class FileDownloadMixin:
  "This class downloads files to a directory of your choosing"
  # Classes that extend this must require 'anaconda-version',
  # 'base-info' and 'installer-repo'.
  def __init__(self):
    self.file_locals = None

  def setup(self):
    paths = []
    for data in self.file_locals.values():
      rinfix = data['path'] % self.cvars['base-info']
      linfix = data['path'] % self.cvars['distribution-info']
      self.io.add_fpath(self.cvars['installer-repo'].url/rinfix,
                        (self.SOFTWARE_STORE/linfix).dirname,
                        id='FileDownloadMixin')

  def apply(self):
    self.io.clean_eventcache()

  def _download(self):
    self.io.sync_input(what='FileDownloadMixin', cache=True)


class InvalidImageFormatError(StandardError):
  message = ( "Error reading image file '%(image)s': invalid format: expected "
              "%(expected)s, got %(got)s" )
