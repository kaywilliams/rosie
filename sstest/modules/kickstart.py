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
from systemstudio.errors import SystemStudioError

from sstest        import EventTestCase, ModuleTestSuite
from sstest.core   import make_extension_suite
from sstest.mixins import touch_input_files, remove_input_files

class KickstartEventTestCase(EventTestCase):
  moduleid = 'kickstart'
  eventid  = 'kickstart'
  _conf = """<kickstart>infile</kickstart>"""

  def setUp(self):
    EventTestCase.setUp(self)
    if self.event:
      touch_input_files(self.event._config.file.abspath().dirname)

  def tearDown(self):
    if self.event:
      remove_input_files(self.event._config.file.abspath().dirname)
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

  def runTest(self):
   self.tb.dispatch.execute(until=self.event)
   for item in self.event.adds:
     self.failUnless(item['text'] in self.event.ksfile.read_text())

class Test_KickstartFailsOnInvalidInput(KickstartEventTestCase):
  "kickstart fails on invalid input"
  _conf = """<kickstart content='text'>invalid</kickstart>"""

  def runTest(self):
   self.execute_predecessors(self.event)
   self.failUnlessRaises(SystemStudioError, self.event)

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('kickstart')

  suite.addTest(make_extension_suite(KickstartEventTestCase, distro, version, arch))
  suite.addTest(Test_KickstartFromText(distro, version, arch))
  suite.addTest(Test_KickstartIncludesAdditions(distro, version, arch))
  suite.addTest(Test_KickstartFailsOnInvalidInput(distro, version, arch))

  return suite
