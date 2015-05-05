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

from deploy.util.pps.Path    import Path_Walk
from deploy.util.pps.PathSet import PathSet

from error import error_transform

class LocalPath_Walk(Path_Walk):

  def listdir(self, glob=None, nglob=None, all=False, sort='name'):
    pathset = PathSet([ self/x for x in os.listdir(self.normpath()) ])

    if not all: pathset.fnmatch('.*', invert=True) # remove dotfiles
    if glob:  pathset.fnmatch(glob)
    if nglob: pathset.fnmatch(nglob, invert=True)
    if sort:  pathset.sort(type=sort)

    return pathset

  _protect = ['listdir']

for fn in LocalPath_Walk._protect:
  setattr(LocalPath_Walk, fn, error_transform(getattr(LocalPath_Walk, fn)))
