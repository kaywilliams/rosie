#
# Copyright (c) 2012
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
from centosstudio.util import pps
from centosstudio.util import rxml

from cstest      import EventTestCase, ModuleTestSuite, _run_make
from cstest.core import make_core_suite


class RepomdEventTestCase(EventTestCase):
  moduleid = 'repomd'
  eventid  = 'repomd'
  _type = 'package'

class Test_CompsFile(RepomdEventTestCase):
  "comps file included in repodata"
  _type = 'system'
  _conf = '<packages><package>kernel</package></packages>'
  def runTest(self):
    self.tb.dispatch.execute(until=self.id)
    self.failUnlessExists(self.event.cvars['repomd-file'].dirname /
                          self.event.cvars['groupfile'].basename)


def make_suite(distro, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname/'shared')

  suite = ModuleTestSuite('repomd')

  suite.addTest(make_core_suite(RepomdEventTestCase, distro, version, arch))
  suite.addTest(Test_CompsFile(distro, version, arch))

  return suite
