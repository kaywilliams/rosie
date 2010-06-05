#
# Copyright (c) 2010
# Solution Studio. All rights reserved.
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

from solutionstudio.util import magic
from solutionstudio.util import pps
from solutionstudio.util import shlib
from solutionstudio.util import sync

from solutionstudio.util.img import acquire_mount_point, release_mount_point, MODE_WRITE, MODE_READ

from solutionstudio.util.img.errors import ImageIOError
from solutionstudio.util.img.image  import Image

IMAGES = [
  {
    'format': magic.FILE_TYPE_CPIO,
    'aliases': [magic.FILE_TYPE_CPIO, 'cpio'],
    'class': 'CpioImageHandler',
    'factory': 'MakeCpioImage',
    'rpms': ['cpio'],
  },
]

class CpioImageHandler:
  def __init__(self, base):
    self.base = base
    self._mount = None
    self._capacity = -1 # unlimited

  def getsize(self):
    return self.base.imgloc.du()

  def getcapacity(self):
    return self._capacity

  def open(self, mode=MODE_WRITE, point=None):
    if not point:
      point = acquire_mount_point()
    if mode == MODE_WRITE:
      oldcwd = os.getcwd()
      os.chdir(point)
      shlib.execute('cpio -i -d --quiet -m < "%s"' % self.base.imgloc)
      os.chdir(oldcwd)
    self._mount = point

  def close(self):
    self.flush()
    release_mount_point(self._mount)
    self._mount = None

  def flush(self):
    if self.base.mode == MODE_WRITE:
      oldcwd = os.getcwd()
      os.chdir(self._mount)
      shlib.execute('find . | cpio --quiet -c -o -a > "%s"' % self.base.imgloc)
      os.chdir(oldcwd)

  def write(self, src, dest='/'):
    imgdir = self._mount//dest
    imgdir.mkdirs()
    for item in src:
      sync.sync(item, imgdir)

  def copy(self, image1, image2):
    image2.write(image1._mount.listdir(all=True), '/')

  def remove(self, file):
    self._mount//file.rm(recursive=True)

  def list(self, relative=False):
    self.flush()
    files = shlib.execute('cpio --list --quiet < "%s"' % self.base.imgloc)
    # the archive always contains '.', which we do not want to list
    files = [ f for f in files if f != '.' ] # kind of a hack...
    if relative:
      return pps.PathSet.PathSet(files)
    else:
      return pps.PathSet.PathSet([ self._mount/x for x in files ])

  def read(self, fn):
    if self.base.mode == MODE_READ:
      oldcwd = os.getcwd()
      os.chdir(self._mount)
      shlib.execute('cpio -i -d -m --quiet "%s" < "%s"' % (fn, self.base.imgloc))
      os.chdir(oldcwd)

    f = self._mount//fn

    if not f.exists():
      raise ImageIOError("'%s' not found in image" % fn)
    elif f.isdir():
      raise ImageIOError("'%s' is a directory" % fn)
    else:
      return f.open()

def MakeCpioImage(file, zipped=False):
  "Make a new CPIO image"
  file = pps.path(file)
  if not file.isfile():
    shlib.execute('echo | cpio --quiet -c -o -a > "%s"' % file) # create empty cpio archive

  image = Image(file, zipped=zipped)
  image.handler = CpioImageHandler(image)
  return image
