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
from rendition import pps
from rendition import xmllib

from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_core_suite

class LogosEventTestCase(EventTestCase):
  moduleid = 'logos'
  eventid  = 'logos'

class Test_LogosEvent_Default(LogosEventTestCase):
  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('logos-rpm', self.event._config, attrs={'enabled': 'False'})

  def runTest(self):
    self.tb.dispatch.execute(until='logos')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosEvent_Custom(LogosEventTestCase):
  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('logos-rpm', self.event._config, attrs={'enabled': 'True'})

  def runTest(self):
    self.tb.dispatch.execute(until='logos')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('logos')

  suite.addTest(make_core_suite(LogosEventTestCase, distro, version, arch))
  suite.addTest(Test_LogosEvent_Default(distro, version, arch))
  suite.addTest(Test_LogosEvent_Custom(distro, version, arch))

  return suite
