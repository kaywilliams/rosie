#
# Copyright (c) 2011
# OpenProvision, Inc. All rights reserved.
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
from openprovision.errors import OpenProvisionError

from optest        import EventTestCase, ModuleTestSuite
from optest.core   import make_extension_suite
from optest.mixins import touch_input_files, remove_input_files

class KickstartEventTestCase(EventTestCase):
  moduleid = 'kickstart'
  eventid  = 'kickstart'
  _conf = """<kickstart>/tmp/optest/infile</kickstart>"""

  def setUp(self):
    EventTestCase.setUp(self)
    if self.event:
      touch_input_files(self.buildroot)

  def tearDown(self):
    if self.event:
      remove_input_files(self.buildroot)
    EventTestCase.tearDown(self)

class Test_KickstartFromText(KickstartEventTestCase):
  "kickstart created from text input"
  _conf = """<kickstart content='text'></kickstart>"""

  def setUp(self):
    EventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnlessExists(self.event.ksfile)

  def tearDown(self):
    EventTestCase.tearDown(self)

class Test_KickstartIncludesAdditions(KickstartEventTestCase):
  "kickstart includes additional items"
  _conf = """<kickstart content='text'></kickstart>"""

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
   self.tb.dispatch.execute(until=self.event)
   for item in self.event.locals.L_KICKSTART_ADDS:
     self.failUnless(self.event.locals.L_KICKSTART_ADDS[item]['text'] in 
                     self.event.ksfile.read_text())

  def tearDown(self):
    EventTestCase.tearDown(self)

class Test_KickstartFailsOnInvalidInput(KickstartEventTestCase):
  "kickstart fails on invalid input"
  _conf = """<kickstart content='text'>invalid</kickstart>"""

  def runTest(self):
   self.execute_predecessors(self.event)
   if self.event.cvars['pykickstart-version'] < '1.74' and self.event.cvars['base-info']['version'][:1] >= '6':
     pass # el5 pykickstart can't validate el6 files
   else:
     self.failUnlessRaises(OpenProvisionError, self.event)

  def tearDown(self):
    EventTestCase.tearDown(self)

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('kickstart')

  suite.addTest(make_extension_suite(KickstartEventTestCase, distro, version, arch))
  suite.addTest(Test_KickstartFromText(distro, version, arch))
  suite.addTest(Test_KickstartIncludesAdditions(distro, version, arch))
  suite.addTest(Test_KickstartFailsOnInvalidInput(distro, version, arch))

  return suite
