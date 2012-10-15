#
# Copyright (c) 2012
# System Studio Project. All rights reserved.
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
from systemstudio.util import listcompare

from systemstudio.modules.shared.bootoptions  import *
from systemstudio.modules.shared.csshelve     import *
from systemstudio.modules.shared.depsolver    import *
from systemstudio.modules.shared.execute      import *
from systemstudio.modules.shared.installer    import *
from systemstudio.modules.shared.input        import * # requires execute
from systemstudio.modules.shared.kickstart    import *
from systemstudio.modules.shared.publishsetup import *
from systemstudio.modules.shared.repomd       import *
from systemstudio.modules.shared.repos        import *
from systemstudio.modules.shared.deploy       import * # requires execute, input
from systemstudio.modules.shared.rpmbuild     import * # requires shelve
from systemstudio.modules.shared.config       import * # requires rpmbuild
from systemstudio.modules.shared.release      import * # requires rpmbuild
from systemstudio.modules.shared.testpublish  import * # requires config

class ListCompareMixin:
  def __init__(self, lfn=None, rfn=None, bfn=None, cb=None):
    self.lfn = lfn
    self.rfn = rfn
    self.bfn = bfn
    self.cb  = cb

    self.l = None
    self.r = None
    self.b = None

  def compare(self, l1, l2):
    self.l, self.r, self.b = listcompare.compare(l1, l2)

    if len(self.b) > 0:
      if self.cb:
        self.cb.notify_both(len(self.b))
      if self.bfn:
        for i in self.b: self.bfn(i)
    if len(self.l) > 0:
      if self.cb:
        self.cb.notify_left(len(self.l))
      if self.lfn:
        for i in self.l: self.lfn(i)
    if len(self.r) > 0:
      if self.cb:
        self.cb.notify_right(len(self.r))
      if self.rfn:
        for i in self.r: self.rfn(i)
