#
# Copyright (c) 2011
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
from cstest      import EventTestCase, ModuleTestSuite
from cstest.core import make_core_suite

non_meta_event = 'packages'
meta_event = 'setup'

class AutocleanEventTestCase(EventTestCase):
  moduleid = 'autoclean'
  eventid  = 'autoclean'

class Test_NonMeta(AutocleanEventTestCase):
  "standard run (non-meta events)"
  def setUp(self):
    AutocleanEventTestCase.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 0

    self.clean_event_md(self.non_meta_event)
    self.clean_event_md()

  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failUnlessRuns(self.non_meta_event)

class Test_NonMetaVersion(AutocleanEventTestCase):
  "Event.run() executes on Event.event_version change"
  def setUp(self):
    AutocleanEventTestCase.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 1

  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failUnlessRuns(self.non_meta_event)

class Test_NonMetaNoVersion(AutocleanEventTestCase):
  "Event.run() does not execute when Event.event_version unchanged"
  def setUp(self):
    AutocleanEventTestCase.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 1

  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failIfRuns(self.non_meta_event)

class Test_Meta(AutocleanEventTestCase):
  "standard run (meta events)"
  def setUp(self):
    AutocleanEventTestCase.setUp(self)
    self.meta_event = self.event._getroot().get(meta_event)
    self.meta_event.event_version = 0

    self.clean_event_md(self.meta_event)
    for event in self.meta_event.get_children():
      self.clean_event_md(event)
    self.clean_event_md()

  def runTest(self):
    self.execute_predecessors(self.meta_event)
    for event in [self.meta_event] + self.meta_event.get_children():
      self.failUnlessRuns(event)

class Test_MetaVersion(AutocleanEventTestCase):
  "Event.run() executes on Event.event_version change (and all children)"
  def setUp(self):
    AutocleanEventTestCase.setUp(self)
    self.meta_event = self.event._getroot().get(meta_event)
    self.meta_event.event_version = 1

  def runTest(self):
    self.execute_predecessors(self.meta_event)
    for event in [self.meta_event] + self.meta_event.get_children():
      self.failUnlessRuns(event)

class Test_MetaNoVersion(AutocleanEventTestCase):
  "Event.run() does not execute when Event.event_version unchanged (and all children)"
  def setUp(self):
    AutocleanEventTestCase.setUp(self)
    self.meta_event = self.event._getroot().get(meta_event)
    self.meta_event.event_version = 1

  def runTest(self):
    self.execute_predecessors(self.meta_event)
    for event in [self.meta_event] + self.meta_event.get_children():
      self.failIfRuns(event)

class Test_RemoveDisabled(AutocleanEventTestCase):
  "remove disabled event directories"
  def setUp(self):
    AutocleanEventTestCase.setUp(self)
    self.test_dir = self.event.METADATA_DIR/'test_disabled_event'
    self.test_dir.mkdirs()

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failIfExists(self.test_dir)

  def tearDown(self):
    if self.test_dir.exists(): self.test_dir.remove()
    AutocleanEventTestCase.tearDown(self)


def make_suite(distro, version, arch):
  suite = ModuleTestSuite('autoclean')

  # autoclean
  suite.addTest(make_core_suite(AutocleanEventTestCase, distro, version, arch))
  suite.addTest(Test_NonMeta(distro, version, arch))
  suite.addTest(Test_NonMetaVersion(distro, version, arch))
  suite.addTest(Test_NonMetaNoVersion(distro, version, arch))
  suite.addTest(Test_Meta(distro, version, arch))
  suite.addTest(Test_MetaVersion(distro, version, arch))
  suite.addTest(Test_MetaNoVersion(distro, version, arch))
  suite.addTest(Test_RemoveDisabled(distro, version, arch))

  return suite