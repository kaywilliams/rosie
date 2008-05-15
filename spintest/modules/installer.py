#
# Copyright (c) 2007, 2008
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
from rendition.xmllib import config

from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class InstallerSetupEventTestCase(EventTestCase):
  moduleid = 'installer'
  eventid  = 'installer-setup'

class InstallerEventTestCase(EventTestCase):
  moduleid = 'installer'
  eventid  = 'installer'

class Test_NoBase(InstallerSetupEventTestCase):
  "without base and installer sections, raises RuntimeError"
  _conf = ["<base/>", "<installer/>"]

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)

#class Test_BaseDefaults(InstallerSetupEventTestCase): # handled by base test cases

class Test_InstallerDefaults(InstallerSetupEventTestCase):
  "defaults defined in installer section are used"
  # the stuff this thing tests is technically used in every event test case already
  def runTest(self):
    self.tb.dispatch.execute(until='installer-setup')
    self.failUnless(self.event.repos.has_key('installer'))
    self.failUnlessEqual(len(self.event.repos), 1)
    self.failIf(self.event.repos['installer'].mirrorlist)


def make_suite(distro, version, arch):
  suite = ModuleTestSuite('installer')

  # installer-setup
  suite.addTest(make_core_suite(InstallerSetupEventTestCase, distro, version, arch))
  suite.addTest(Test_NoBase(distro, version, arch))
  #suite.addTest(Test_BaseDefaults(distro, version, arch)) # see above
  suite.addTest(Test_InstallerDefaults(distro, version, arch))

  # installer
  suite.addTest(make_core_suite(InstallerEventTestCase, distro, version, arch))

  return suite
