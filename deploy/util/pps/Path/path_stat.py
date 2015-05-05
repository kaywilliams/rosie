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
import stat

from deploy.util.pps.Path.error import PathError

class Path_Stat(object):
  "Stat methods for Path objects"

  # stat() calls
  def stat(self):     raise NotImplementedError()
  def lstat(self):    raise NotImplementedError()

  # file properties
  def exists(self):
    try:
      self.stat()
    except PathError:
      return False
    return True
  def isdir(self):    return stat.S_ISDIR(self.stat().st_mode)
  def isfile(self):   return stat.S_ISREG(self.stat().st_mode)
  def islink(self):   return stat.S_ISLNK(self.stat().st_mode)

  # file metadata
  def getatime(self): raise NotImplementedError()
  def getmtime(self): raise NotImplementedError()
  def getctime(self): raise NotImplementedError()
  def getsize(self):  raise NotImplementedError()

  atime = property(getatime)
  mtime = property(getmtime)
  ctime = property(getctime)
  size  = property(getsize)
