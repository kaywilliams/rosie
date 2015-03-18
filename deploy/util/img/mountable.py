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
import time

from deploy.util import pps
from deploy.util import shlib
from deploy.util import sync

from deploy.util.img import acquire_mount_point, release_mount_point, MODE_WRITE
from deploy.util.img.errors import ImageIOError
from deploy.util.img.image  import Image

UMOUNT_ATTEMPTS = 1
UMOUNT_RETRY_TIME = 2 # seconds

class MountableImageHandler:
  def __init__(self, base):
    self.base = base
    self._mount = None
    self._type = None # type string as used by mount to determine filesystem type
    self.udisks2 = udisks2_active()

  def getsize(self):
    return self._mount.du(bytes=True)

  def getcapacity(self):
    return self.base.imgloc.stat().st_size

  def open(self, mode=MODE_WRITE, point=None):


    if self.udisks2:
      shlib.execute('systemctl stop udisks2')

    if not point:
      point = acquire_mount_point()
    mounted = False
    for mounts in pps.path('/proc/mounts').read_lines():
      if self.base.imgloc in mounts:
        mounted = True; break
    if mode == MODE_WRITE and mounted:
      import warnings
      warnings.warn("file '%s' is already mounted somewhere on the filesystem. "
                    "Any img-related errors that occur are most likely the "
                    "result of this.\nContent of '/proc/mounts is:\n%s"
                    % (mounted, pps.path('/proc/mounts').read_text()))
    shlib.execute('/bin/mount -o loop -t %s "%s" "%s"' % (self._type, self.base.imgloc, point))
    self._mount = point

    # get rid of pesky lost+found folder
    (self._mount/'lost+found').rm(recursive=True, force=True)

  def close(self):
    count = 0
    while True:
      try:
        shlib.execute('/bin/umount %s' % self._mount)
      except shlib.ShExecError, e:
        # earlier versions of umount used retcode 1 for device busy errors
        # current versions (e.g. util-linux 2.23.2) use retcode 32; 
        if count >= UMOUNT_ATTEMPTS or e.retcode not in [1, 32]:
          raise
        else:
          # device may be busy
          time.sleep(UMOUNT_RETRY_TIME)
          count += 1
      else:
        break
    
    if self.udisks2:
      shlib.execute('systemctl start udisks2')
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


def MakeMountableImage(cls, fsmaker, file, zipped=False, size=1*1024**2, 
                       **kwargs):

  udisks2 = udisks2_active()

  file = pps.path(file)
  if not file.isfile():
    if udisks2:
      shlib.execute('systemctl stop udisks2')
    if size % 512 != 0:
      numblks = (size/512) + 1
    else:
      numblks = size/512
    shlib.execute('/bin/dd if=/dev/zero of="%s" bs=512 count=%s' % 
                 (file, numblks))
    shlib.execute(fsmaker)
    if udisks2:
      shlib.execute('systemctl start udisks2')

  image = Image(file, zipped=zipped)
  image.udisks2 = udisks2
  image.handler = cls(image)
  return image

def udisks2_active():
  # udisks2 thwarts our efforts to mount disks at specified locations,
  # determine if it is active, so that we can disable it temporarily as needed
  try:
    shlib.execute('systemctl status udisks2')
    udisks2 = True
  except shlib.ShExecError:
    udisks2 = False

  return udisks2
