#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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
import inspect
import socket
import unittest

from dtest import EventTestCase, EventTestCaseDummy, decorate

from deploy.errors import DeployError

import functools
from functools import wraps

class EventTestCaseHeader(EventTestCaseDummy):
  separator1 = '=' * 70
  separator2 = '-' * 70
  def __init__(self, eventid, os, version, arch):
    self.eventid = eventid
    self.os  = os
    self.version = version
    self.arch    = arch
    EventTestCaseDummy.__init__(self)

  def shortDescription(self):
    test_info = "testing event '%s' (%s-%s-%s)" \
                 % (self.eventid, self.os, self.version, self.arch)

    return '\n'.join(['', self.separator1, test_info, self.separator2])

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

def make_core_suite(TestCase, os, version, arch, conf=None, offline=True):
  suite = CoreTestSuite()

  # hack-ish solution to get a pretty header
  suite.addTest(EventTestCaseHeader(TestCase.eventid, os, version, arch))

  suite.addTest(CoreEventTestCase01(TestCase(os, version, arch, conf)))
  suite.addTest(CoreEventTestCase02(TestCase(os, version, arch, conf)))

  if offline:
    suite.addTest(CoreEventTestCase03(TestCase(os, version, arch, conf)))

  suite.addTest(CoreEventTestCase04(TestCase(os, version, arch, conf)))
  suite.addTest(CoreEventTestCase05(TestCase(os, version, arch, conf)))
  suite.addTest(CoreEventTestCase06(TestCase(os, version, arch, conf)))
  return suite

def make_extension_suite(TestCase, os, version, arch, conf=None, offline=True):
  suite = CoreTestSuite()
  suite.addTest(make_core_suite(TestCase, os, version, arch, conf, offline))
  suite.addTest(ExtensionEventTestCase00(TestCase(os, version, arch, conf)))
  suite.addTest(ExtensionEventTestCase01(TestCase(os, version, arch, conf)))
  return suite


def CoreEventTestCase01(self):
  self._testMethodDoc = "Event.run() executes if neither force nor skip specified"

  def post_setup():
    self.event.status = None
    self.clean_event_md()

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRuns(self.event)
    result = self.event.verify()
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
    result = self.event.verify()
    self.failUnless(result.wasSuccessful(), '\n'+result._strErrors())

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  return self

def CoreEventTestCase03(self):
  self._testMethodDoc = "Socket methods not called in offline mode"
  self.socket_orig = {} # dict for saving/restoring socket methods

  # wrap calls to socket raising a Runtime Error if they are called
  def socket_wrapper(fn):
    # see http://bugs.python.org/issue3445 
    @wraps(fn, set(functools.WRAPPER_ASSIGNMENTS) & set(dir(fn)))
    def wrapped(*args, **kwargs):
      raise RuntimeError("call to socket")
    return wrapped

  def post_setup():
    self.event.status = None
    self.clean_event_md()
    self.event.cache_handler.offline = True 
    for n, v in inspect.getmembers(socket, inspect.isroutine) + \
                inspect.getmembers(socket, inspect.isclass):
      self.socket_orig[n] = v
      setattr(socket, n, socket_wrapper(v))

  def runTest():
    self.tb.dispatch.execute(until=self.eventid)

  def pre_teardown():
    self.event.cache_handler.offline = False 
    for n, v in inspect.getmembers(socket, inspect.isroutine):
      setattr(socket, n, self.socket_orig[n])

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  decorate(self, 'tearDown', prefn=pre_teardown)
  return self

def CoreEventTestCase04(self):
  self._testMethodDoc = "Event.run() executes with --force"

  def post_setup():
    self.event.status = True

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRuns(self.event)
    result = self.event.verify()
    self.failUnless(result.wasSuccessful(), '\n'+result._strErrors())

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  return self

def CoreEventTestCase05(self):
  self._testMethodDoc = "Event.run() does not execute with --skip"

  def post_setup():
    self.event.status = False

  def runTest():
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    result = self.event.verify()
    self.failUnless(result.wasSuccessful(), '\n'+result._strErrors())

  decorate(self, 'setUp', postfn=post_setup)
  self.runTest = runTest
  return self

def CoreEventTestCase06(self):
  self._testMethodDoc = "Event.verify_*() methods are successful"

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    result = self.event.verify()
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

  def tearDown(): # go straight to base tearDown since event didn't actually run
    EventTestCase.tearDown(self)

  decorate(self, 'setUp', prefn=pre_setup)
  self.runTest = runTest
  self.tearDown = tearDown
  return self
