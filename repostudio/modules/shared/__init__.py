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
from repostudio.util import listcompare

from repostudio.modules.shared.bootoptions  import *
from repostudio.modules.shared.csshelve     import *
from repostudio.modules.shared.depsolver    import *
from repostudio.modules.shared.execute      import *
from repostudio.modules.shared.installer    import *
from repostudio.modules.shared.input        import * # requires execute
from repostudio.modules.shared.kickstart    import *
from repostudio.modules.shared.publishsetup import *
from repostudio.modules.shared.repomd       import *
from repostudio.modules.shared.repos        import *
from repostudio.modules.shared.deploy       import * # requires execute, input
from repostudio.modules.shared.rpmbuild     import * # requires shelve
from repostudio.modules.shared.config       import * # requires rpmbuild
from repostudio.modules.shared.release      import * # requires rpmbuild
from repostudio.modules.shared.testpublish  import * # requires config

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
