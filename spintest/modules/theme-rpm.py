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
from spintest.core import make_core_suite, make_extension_suite
from spintest.rpms import RpmBuildMixinTestCase, RpmCvarsTestCase

class ThemeRpmEventTestCase(EventTestCase):
  moduleid = 'theme-rpm'
  eventid  = 'theme-rpm'
  _conf = """<theme-rpm enabled="true"/>"""

class Test_ThemeRpmBuild(RpmBuildMixinTestCase, ThemeRpmEventTestCase):
  def setUp(self):
    ThemeRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ThemeRpmCvars1(RpmCvarsTestCase, ThemeRpmEventTestCase):
  def setUp(self):
    ThemeRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ThemeRpmCvars2(RpmCvarsTestCase, ThemeRpmEventTestCase):
  def setUp(self):
    ThemeRpmEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('theme-rpm')

  suite.addTest(make_extension_suite(ThemeRpmEventTestCase, basedistro, arch))
  suite.addTest(Test_ThemeRpmBuild(basedistro, arch))
  suite.addTest(Test_ThemeRpmCvars1(basedistro, arch))
  suite.addTest(Test_ThemeRpmCvars2(basedistro, arch))

  return suite
