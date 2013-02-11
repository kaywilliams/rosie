#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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

from deploy.util import magic
from deploy.util import shlib

from deploy.util.img import acquire_mount_point, release_mount_point

from deploy.util.img.mountable import MountableImageHandler, MakeMountableImage

IMAGES = [
  {
    'format': magic.FILE_TYPE_FAT,
    'aliases': [magic.FILE_TYPE_FAT, 'fat', 'fat16', 'fat32'],
    'class': 'FatImageHandler',
    'factory': 'MakeFatImage',
    'rpms': ['dosfstools'],
  },
]

class FatImageHandler(MountableImageHandler):
  def __init__(self, base):
    MountableImageHandler.__init__(self, base)
    self._type = 'vfat'

  def _resize(self, size):
    point = acquire_mount_point()
    newimgpath = point/'%s.new' % self.base.name
    newimg = MakeFatImage(newimgpath, size=size)

    self.open()
    newimg.open()
    self.base.copyto(newimg)
    self.close()
    newimg.close()

    del newimg
    newimgpath.move(self.base.imgloc)
    release_mount_point(point)

def MakeFatImage(file, zipped=False, size=1*1024**2, **kwargs):
  "Create a new FAT image.  If size is not specified, defaults to 1MB"
  return MakeMountableImage(FatImageHandler, '/sbin/mkdosfs %s' % file,
                            file, zipped=zipped, size=size, **kwargs)
