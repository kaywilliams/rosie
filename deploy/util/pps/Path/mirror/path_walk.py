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
import errno

from deploy.util.pps.lib.mirror import trymirrors, ContinueIteration
from deploy.util.pps.Path.error import PathError
from deploy.util.pps.PathSet    import PathSet

from deploy.util.pps.Path.remote import RemotePath_Walk

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
