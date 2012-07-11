#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
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
import shutil

from centosstudio.util import pps
from centosstudio.util import shlib

from centosstudio.util.img import MODES, MODE_READ, MODE_WRITE, acquire_mount_point
from centosstudio.util.img.image  import Image
from centosstudio.util.img.errors import *


class ReadOnlyImageHandler:
  def flush(self):
    raise ReadOnlyError()

  def open(self, mode=MODE_WRITE, point=None):
    if mode == MODE_WRITE:
      raise ReadOnlyError()

    if not point:
      point = acquire_mount_point()
    mounted = False
    for mounts in pps.path('/proc/mounts').read_lines():
      if mounts.find(self.base.imgloc) != -1:
        mounted = True; break
    if mode == MODE_WRITE and mounted:
      import warnings
      warnings.warn("file '%s' is already mounted somewhere on the filesystem. "
                    "Any img-related errors that occur are most likely the "
                    "result of this.\nOutput of `mount` is:\n%s" % mounted)
    shlib.execute('/bin/mount -o loop -t %s "%s" "%s"' % 
                 (self._type, self.base.imgloc, point))
    self._mount = point

  def write(self, src, dst='/'):
    if self.closed:
      raise ImageIOError(ERROR_WRITE % 'image is closed')
    if self.mode == MODE_READ:
      raise ImageIOError(ERROR_WRITE % 'opened in read mode')
    raise ReadOnlyError()

  def writeflo(self, fsrc, filename, dst='/'):
    "hack method of writing a file like object"
    raise ReadOnlyError()

  def copyfrom(self, image):
    "Copy the contents of image into self"
    raise ReadOnlyError()

  def remove(self, file):
    raise ReadOnlyError()


def MakeReadOnlyImage(cls, file, zipped=False, **kwargs):
  file = pps.path(file)
  if not file.isfile():
    raise ReadOnlyError()

  image = Image(file, zipped=zipped)
  image.handler = cls(image)
  return image


class ReadOnlyError(StandardError):
  def __str__(self):
    return "Image is read-only"
