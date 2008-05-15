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
from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite
from spintest.rpms import RpmBuildMixinTestCase, RpmCvarsTestCase

class LogosRpmEventTestCase(EventTestCase):
  moduleid = 'logos-rpm'
  eventid  = 'logos-rpm'
  _conf = """<logos-rpm enabled="true"/>"""

class Test_LogosRpmBuild(RpmBuildMixinTestCase, LogosRpmEventTestCase):
  def setUp(self):
    LogosRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmCvars1(RpmCvarsTestCase, LogosRpmEventTestCase):
  def setUp(self):
    LogosRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmCvars2(RpmCvarsTestCase, LogosRpmEventTestCase):
  def setUp(self):
    LogosRpmEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('logos-rpm')

  suite.addTest(make_core_suite(LogosRpmEventTestCase, distro, version, arch))
  suite.addTest(Test_LogosRpmBuild(distro, version, arch))
  suite.addTest(Test_LogosRpmCvars1(distro, version, arch))
  suite.addTest(Test_LogosRpmCvars2(distro, version, arch))

  return suite
