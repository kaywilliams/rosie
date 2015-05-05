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
import os
import errno

from deploy.util.pps.Path.error import PathError
from deploy.util.pps.Path.local.error import error_transform

from deploy.util.pps.Path.local import LocalPath_IO

class PosixPath_IO(LocalPath_IO):

  # file metadata modification functions
  def chown(self, uid, gid): os.chown(self.normpath(), uid, gid)

  # file/directory creation/modification
  def _link(self, new):
    try:
      os.link(self.normpath(), new)
    except (OSError, IOError), e:
      if e.errno == errno.ENOENT:
        raise PathError(e.errno, strerror="cannot create link '%s' to '%s': %s"
                        % (new, self.normpath(), e.strerror))
      else: raise

  def _symlink(self, new):
    try:
      os.symlink(self.normpath(), new)
    except (OSError, IOError), e:
      if e.errno == errno.ENOENT:
        raise PathError(e.errno, strerror="cannot create symlink '%s' to '%s': "
                        "%s" % (new, self.normpath(), e.strerror))
      else: raise

  def readlink(self):     return self._new(os.readlink(self.normpath()))

  _protect = ['chown', '_link', '_symlink', 'readlink']

for fn in PosixPath_IO._protect:
  setattr(PosixPath_IO, fn, error_transform(getattr(PosixPath_IO, fn)))
