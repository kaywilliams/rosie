#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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

from repostudio.util.pps.lib.mirror import trymirrors, ContinueIteration
from repostudio.util.pps.Path.error import PathError
from repostudio.util.pps.PathSet    import PathSet

from repostudio.util.pps.Path.remote import RemotePath_Walk

class MirrorPath_Walk(RemotePath_Walk):
  "Path iteration/walking functions"
  @trymirrors
  def listdir(self, f, *a,**kw):
    r = PathSet()
    for i in f.listdir(*a, **kw):
      p = (self//i.relpathfrom(f)).normpath()
      # update stat values - i.stat() should not result in remote call
      p._set_stat(i.stat())
      r.append(p)

    return r
