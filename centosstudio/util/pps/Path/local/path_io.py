#
# Copyright (c) 2011
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
import os
import shutil

from error import error_transform

from centosstudio.util.pps.Path import Path_IO

class LocalPath_IO(Path_IO):

  # file metadata modification functions
  def utime(self, times):     os.utime(self.normpath(), times)
  def chmod(self, mode):      os.chmod(self.normpath(), mode)

  # file/directory creation/modification
  def rename(self, new):      os.rename(self.normpath(), new)
  def move(self, new):        shutil.move(self.normpath(), new)
  def mkdir(self, mode=0777): os.mkdir(self.normpath(), mode)
  def rmdir(self):            os.rmdir(self.normpath())
  def mknod(self):            os.mknod(self.normpath())
  def touch(self):
    fd = os.open(self.normpath(), os.O_WRONLY | os.O_CREAT, 0666)
    os.close(fd)
    self.utime(None) # update access/modify times to now
  def remove(self):           os.remove(self.normpath())
  def unlink(self):           os.unlink(self.normpath())

  def open(self, mode='r', seek=None):
    if not seek:
      return open(self.normpath(), mode)
    else:
      fo = open(self.normpath(), mode)
      fo.seek(seek)
      return fo

  _protect = ['utime', 'chmod', 'rename', 'mkdir', 'rmdir', 'mknod',
              'touch', 'remove', 'unlink', 'open']

for fn in LocalPath_IO._protect:
  setattr(LocalPath_IO, fn, error_transform(getattr(LocalPath_IO, fn)))
