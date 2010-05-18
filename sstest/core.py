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
import unittest

from sbtest import EventTestCaseDummy, decorate

from systembuilder.errors import SystemBuilderError

class EventTestCaseHeader(EventTestCaseDummy):
  separator1 = '=' * 70
  separator2 = '-' * 70
  def __init__(self, eventid, distro, version, arch):
    self.eventid = eventid
    self.distro  = distro
    self.version = version
    self.arch    = arch
    EventTestCaseDummy.__init__(self)

  def shortDescription(self):
    return '\n'.join(['',
                      self.separator1,
                      "testing event '%s' (%s-%s-%s)"
                        % (self.eventid, self.distro, self.version, self.arch),
                      self.separator2])

class CoreTestSuite(unittest.TestSuite):
  def __init__(self, tests=()):
    unittest.TestSuite.__init__(self, tests)
    self.output = []

  def run(self, result):
    for test in self._tests:
      if result.shouldStop:
        break
      test(result)
      try:
        self.output.extend(test.output)
      except:
        pass
    return result


def make_core_suite(TestCase, distro, version, arch, conf=None):
  suite = CoreTestSuite()

  # hack-ish solution to get a pretty header
  suite.addTest(EventTestCaseHeader(TestCase.eventid, distro, version, arch))

  suite.addTest(CoreEventTestCase00(TestCase(distro, version, arch, conf)))
  suite.addTest(CoreEventTestCase01(TestCase(distro, version, arch, conf)))
  suite.addTest(CoreEventTestCase02(TestCase(distro, version, arch, conf)))
  suite.addTest(CoreEventTestCase03(TestCase(distro, version, arch, conf)))
  suite.addTest(CoreEventTestCase04(TestCase(distro, version, arch, conf)))
  suite.addTest(CoreEventTestCase05(TestCase(distro, version, arch, conf)))
  return suite

def make_extension_suite(TestCase, distro, version, arch, conf=None):
  suite = CoreTestSuite()
  suite.addTest(make_core_suite(TestCase, distro, version, arch, conf))
  suite.addTest(ExtensionEventTestCase00(TestCase(distro, version, arch, conf)))
  suite.addTest(ExtensionEventTestCase01(TestCase(distro, version, arch, conf)))
  return suite


def CoreEventTestCase00(self):
  self._testMethodDoc = "Event.verify() might raise an error if --skip'd first"

  def post_setup():
    self.event.status = False
    self.clean_event_md()

  def runTest():
    self.execute_predecessors(self.event)
    try:
      self.failIfRuns(self.event)
    except (AssertionError, RuntimeError, SystemBuilderError), e:
      pass
    if self.event.diff.handlers.has_key('output'):
      self.failIf(self.event.verifier.unittest().wasSuccessful())

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  return self

def CoreEventTestCase01(self):
  self._testMethodDoc = "Event.run() executes if neither --force nor --skip specified"

  def post_setup():
    self.event.status = None
    self.clean_event_md()

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), '\n'+result._strErrors())

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  return self

def CoreEventTestCase02(self):
  self._testMethodDoc = "Event.run() does not execute after a successful run"

  def post_setup():
    self.event.status = None

  def runTest():
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), '\n'+result._strErrors())

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  return self

def CoreEventTestCase03(self):
  self._testMethodDoc = "Event.run() executes with --force"

  def post_setup():
    self.event.status = True

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), '\n'+result._strErrors())

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  return self

def CoreEventTestCase04(self):
  self._testMethodDoc = "Event.run() does not execute with --skip"

  def post_setup():
    self.event.status = False

  def runTest():
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), '\n'+result._strErrors())

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  return self

def CoreEventTestCase05(self):
  self._testMethodDoc = "Event.verify_*() methods are successful"

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), '\n'+result._strErrors())

  decorate(self, 'setUp')
  self.runTest = runTest
  return self

def ExtensionEventTestCase00(self):
  self._testMethodDoc = "disabling module removes output"

  def pre_setup():
    self.options.disabled_modules.append(self.moduleid)

  def runTest():
    self.tb.dispatch.execute(until='autoclean')
    self.failIfExists(self.tb.dispatch._top.METADATA_DIR/self.eventid)

  def tearDown(): # don't try to append METADATA_DIR to output
    self.tb._lock.release()
    del self.tb
    del self.event

  decorate(self, 'setUp', prefn=pre_setup)
  self.runTest = runTest
  self.tearDown = tearDown
  return self

def ExtensionEventTestCase01(self):
  self._testMethodDoc = "reenabling module regenerates output"

  def pre_setup():
    self.options.disabled_modules.remove(self.moduleid)

  def runTest():
    self.failUnlessExists(self.tb.dispatch._top.METADATA_DIR/self.eventid)

  decorate(self, 'setUp', prefn=pre_setup)
  self.runTest = runTest
  return self
