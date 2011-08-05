#
# Copyright (c) 2011
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

from openprovision.util import magic

from openprovision.util.img import MODE_READ, MODE_WRITE, acquire_mount_point

from openprovision.util.img.readonly  import ReadOnlyImageHandler, MakeReadOnlyImage, ReadOnlyError
from openprovision.util.img.mountable import MountableImageHandler

IMAGES = [
  {
    ##'format': magic.FILE_TYPE_ISO9660,
    'format': 'iso',
    ##'aliases': [magic.FILE_TYPE_ISO9660, 'iso', 'iso9660'],
    'aliases': ['iso', 'iso9660'],
    'class': 'IsoImageHandler',
    'factory': 'MakeIsoImage',
    'rpms': ['genisoimage'], # ?
  },
]

class IsoImageHandler(ReadOnlyImageHandler, MountableImageHandler):
  def __init__(self, base):
    MountableImageHandler.__init__(self, base)
    self._type = 'iso9660'

  def _resize(self, size):
    raise ReadOnlyError()


def MakeIsoImage(file, zipped=False):
  "Create an iso image.  If size is not specified, defaults to 1MB"
  return MakeReadOnlyImage(IsoImageHandler, file, zipped=zipped)
