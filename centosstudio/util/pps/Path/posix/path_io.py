#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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

from centosstudio.util.pps.Path.local.error import error_transform

from centosstudio.util.pps.Path.local import LocalPath_IO

class PosixPath_IO(LocalPath_IO):

  # file metadata modification functions
  def chown(self, uid, gid): os.chown(self, uid, gid)

  # file/directory creation/modification
  def link(self, new):    os.link(self, new)
  def symlink(self, new): os.symlink(self, new)
  def readlink(self):     return self.__class__(os.readlink(self))

  _protect = ['chown', 'link', 'symlink', 'readlink']

for fn in PosixPath_IO._protect:
  setattr(PosixPath_IO, fn, error_transform(getattr(PosixPath_IO, fn)))
