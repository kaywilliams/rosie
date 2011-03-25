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
from systemstudio.util import pps
from systemstudio.util.rxml.config import Element

from sstest      import EventTestCase, ModuleTestSuite
from sstest.core import make_core_suite


class RepomdEventTestCase(EventTestCase):
  moduleid = 'repomd'
  eventid  = 'repomd'


class Test_CompsFile(RepomdEventTestCase):
  "comps file provided"
  def runTest(self):
    self.tb.dispatch.execute(until='repomd')
    self.failUnlessExists(self.event.cvars['repodata-directory'] /
                          self.event.cvars['groupfile'].basename)

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('repomd')

  suite.addTest(make_core_suite(RepomdEventTestCase, distro, version, arch))
  suite.addTest(Test_CompsFile(distro, version, arch))

  return suite
