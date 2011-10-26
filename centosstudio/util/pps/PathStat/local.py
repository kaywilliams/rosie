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
"local.py - definition of locally-based PathStat object"

import os

from __init__ import PathStat

class LocalPathStat(PathStat):
  """
  LocalPathStat objects are identical to PathStat objects except in regard to
  link processing.  When creating a LocalPathStat, the link argument determines
  whether the stat call on LocalPathStat.uri will be on the path itself or the
  target of the link, if the uri refers to a symlink.
  """
  def __init__(self, path, link=False, **kwargs):
    PathStat.__init__(self, path, **kwargs)
    self.link = link

  def stat(self):
    if self.link:
      st = os.lstat(self.uri)
    else:
      st = os.stat(self.uri)

    self.st_blocks  = st.st_blocks
    self.st_blksize = st.st_blksize
    self.st_rdev    = st.st_rdev

    self._stat = list(st)

  def update(self, *args, **kwargs):
    # don't allow updates on local path stats, but don't error either
    pass
