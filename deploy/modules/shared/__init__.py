#
# Copyright (c) 2013
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
from deploy.util import listcompare

from deploy.modules.shared.bootoptions  import *
from deploy.modules.shared.comps        import *
from deploy.modules.shared.dshelve      import *
from deploy.modules.shared.depsolver    import *
from deploy.modules.shared.execute      import *
from deploy.modules.shared.installer    import *
from deploy.modules.shared.input        import * # requires execute
from deploy.modules.shared.kickstart    import *
from deploy.modules.shared.publishsetup import *
from deploy.modules.shared.repomd       import *
from deploy.modules.shared.repos        import *
from deploy.modules.shared.ddeploy      import * # requires execute, input
from deploy.modules.shared.rpmbuild     import * # requires shelve
from deploy.modules.shared.config       import * # requires rpmbuild
from deploy.modules.shared.release      import * # requires rpmbuild
from deploy.modules.shared.testpublish  import * # requires config

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
