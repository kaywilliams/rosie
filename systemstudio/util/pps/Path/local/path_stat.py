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
from systemstudio.util.pps.Path import Path_Stat

from systemstudio.util.pps.PathStat.local import LocalPathStat

from error import error_transform

class LocalPath_Stat(Path_Stat):

  # stat() calls
  def stat(self):  return self._mkstat(populate=True)
  def lstat(self): return self._mkstat(populate=True, link=True)

  # file properties
  def exists(self): return self._pypath.exists(self.normpath())
  def isdir(self):  return self._pypath.isdir(self.normpath())
  def isfile(self): return self._pypath.isfile(self.normpath())
  def islink(self): return self._pypath.islink(self.normpath())

  # file metadata
  def getatime(self): return self._pypath.getatime(self.normpath())
  def getmtime(self): return self._pypath.getmtime(self.normpath())
  def getctime(self): return self._pypath.getctime(self.normpath())
  def getsize(self):  return self._pypath.getsize(self.normpath())

  atime = property(getatime)
  mtime = property(getmtime)
  ctime = property(getctime)
  size  = property(getsize)

  def du(self, bytes=False, count_links=False):
    "Recursively compute disk usage beneath, and including, this path"
    size = 0
    processed = [] # don't double count

    def addfile(file):
      st = file.lstat()
      if not count_links and st.st_ino in processed:
        return 0
      processed.append(st.st_ino)
      return st.st_blocks >> 1

    size += addfile(self)

    if self.isdir():
      for dirs, files, level in self.walk(follow=False):
        for d in dirs:  size += addfile(d)
        for f in files: size += addfile(f)

    if bytes: return size * 1024
    else: return size

  def _mkstat(self, populate=False, link=False):
    stat = LocalPathStat(self.normpath(), link=link)
    if populate: stat.stat()
    return stat

  _protect = ['stat', 'lstat', 'exists', 'isdir', 'isfile', 'islink',
              'getatime', 'getctime', 'getmtime', 'getsize', '_mkstat']

for fn in LocalPath_Stat._protect:
  setattr(LocalPath_Stat, fn, error_transform(getattr(LocalPath_Stat, fn)))
