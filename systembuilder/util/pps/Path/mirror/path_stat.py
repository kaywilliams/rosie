#
# Copyright (c) 2010
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
import errno

from solutionstudio.util.pps.lib.mirror import trymirrors, ContinueIteration, HOSTUNAVAIL

from solutionstudio.util.pps.Path.remote import RemotePath_Stat

from solutionstudio.util.pps.Path.error import PathError

class MirrorPath_Stat(RemotePath_Stat):
  # file properties
  def exists(self):
    try:
      return self._exists()
    except PathError:
      return False

  @trymirrors
  def _exists(self, f):
    try:
      self.stat()
      return True
    except PathError, e:
      if e.errno in HOSTUNAVAIL:
        # host isn't up or is otherwise unreachable
        raise ContinueIteration(err=True)
      else:
        # host is up, file not found
        return False

  @trymirrors
  def _mkstat(self, f, populate=False):
    # returns whatever type of stat that f.stat() returns
    return f._mkstat(populate=populate)
