#
# Copyright (c) 2015
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

from deploy.util import magic
from deploy.util import shlib

from deploy.util.img.mountable import MountableImageHandler, MakeMountableImage

IMAGES = [
  {
    'format': magic.FILE_TYPE_EXT2FS,
    'aliases': [magic.FILE_TYPE_EXT2FS, 'ext2', 'ext3'],
    'class': 'Ext2ImageHandler',
    'factory': 'MakeExt2Image',
    'rpms': ['e2fsprogs'],
  },
]

class Ext2ImageHandler(MountableImageHandler):
  def __init__(self, base):
    MountableImageHandler.__init__(self, base)
    self._type = 'ext2'

  def _resize(self, size):
    shlib.execute('/sbin/resize2fs -f "%s" %sK' % (self.base.imgloc, int(size/1000)))

def MakeExt2Image(file, zipped=False, size=1*1024**2, **kwargs):
  "Create an ext2 image.  If size is not specified, defaults to 1MB"
  return MakeMountableImage(Ext2ImageHandler, '/sbin/mke2fs -F "%s"' % file,
                            file, zipped=zipped, size=size, **kwargs)
