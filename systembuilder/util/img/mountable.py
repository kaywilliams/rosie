#
# Copyright (c) 2010
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

from systembuilder.util import pps
from systembuilder.util import shlib
from systembuilder.util import sync

from systembuilder.util.img import acquire_mount_point, release_mount_point, MODE_WRITE
from systembuilder.util.img.errors import ImageIOError
from systembuilder.util.img.image  import Image

class MountableImageHandler:
  def __init__(self, base):
    self.base = base
    self._mount = None
    self._type = None # type string as used by mount to determine filesystem type

  def getsize(self):
    return self._mount.du(bytes=True)

  def getcapacity(self):
    return self.base.imgloc.stat().st_size

  def open(self, mode=MODE_WRITE, point=None):
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
                    "result of this.\nContent of '/proc/mounts is:\n%s"
                    % (mounted, pps.path('/proc/mounts').read_text()))
    shlib.execute('mount -o loop -t %s "%s" "%s"' % (self._type, self.base.imgloc, point))
    self._mount = point

    # get rid of pesky lost+found folder
    (self._mount/'lost+found').rm(recursive=True, force=True)

  def close(self):
    shlib.execute('umount %s' % self._mount)
    release_mount_point(self._mount)
    self._mount = None

  def flush(self):
    "No-op in mountable images"
    pass

  def write(self, src, dst='/'):
    self._checksize(src, dst)

    imgdir = self._mount//dst
    imgdir.mkdirs()
    for file in src:
      sync.sync(file, imgdir, force=True)

  def _checksize(self, src, dst):
    self.getsize()

    filesize = 0
    imgdir = self._mount//dst
    for s in src:
      file = imgdir/s.basename
      if file.exists():
        filesize -= file.du(bytes=True)
      filesize += s.du(bytes=True)

    # leave a 10% + 1MB buffer
    newsize = int(((filesize + self.getsize()) * 1.1) + 1*1024**2)
    if newsize >= self.getcapacity():
      oldmode = self.base.mode
      self.close()
      self._resize(newsize)
      self.open(oldmode)

  def read(self, fn):
    f = self._mount//fn

    if not f.exists():
      raise ImageIOError, "'%s' not found in image" % fn
    elif f.isdir():
      raise ImageIOError, "'%s' is a directory" % fn
    else:
      return f.open()

  def copy(self, image1, image2):
    image2.write(image1.handler._mount.listdir(all=True), '/')

  def remove(self, file):
    (self._mount//file).rm(recursive=True)

  def list(self, relative=False):
    files = self._mount.findpaths(mindepth=1)
    if relative:
      return files.relpathfrom(self._mount)
    else:
      return files

  def _resize(self):
    raise NotImplementedError


def MakeMountableImage(cls, fsmaker, file, zipped=False, size=1*1024**2):
  file = pps.path(file)
  if not file.isfile():
    if size % 512 != 0:
      numblks = (size/512) + 1
    else:
      numblks = size/512
    shlib.execute('dd if=/dev/zero of="%s" bs=512 count=%s' % (file, numblks))
    shlib.execute(fsmaker)

  image = Image(file, zipped=zipped)
  image.handler = cls(image)
  return image
