import unittest

from dims import pps

from dbtest import EventTestCase, TestBuild, EventTestRunner, EventTestCaseDummy, decorate

class EventTestCaseHeader(EventTestCaseDummy):
  separator1 = '=' * 70
  separator2 = '-' * 70
  def __init__(self, eventid):
    self.eventid = eventid
    EventTestCaseDummy.__init__(self)

  def shortDescription(self):
    return '\n'.join(['', self.separator1,
                      "testing event '%s'" % self.eventid, self.separator2])

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


def make_core_suite(TestCase, basedistro, conf=None):
  suite = CoreTestSuite()
  suite.addTest(EventTestCaseHeader(TestCase.eventid)) # hack to get a pretty header
  suite.addTest(CoreEventTestCase00(TestCase(basedistro, conf)))
  suite.addTest(CoreEventTestCase01(TestCase(basedistro, conf)))
  suite.addTest(CoreEventTestCase02(TestCase(basedistro, conf)))
  suite.addTest(CoreEventTestCase03(TestCase(basedistro, conf)))
  suite.addTest(CoreEventTestCase04(TestCase(basedistro, conf)))
  return suite

def make_extension_suite(TestCase, basedistro, conf=None):
  suite = CoreTestSuite()
  suite.addTest(make_core_suite(TestCase, basedistro, conf))
  suite.addTest(ExtensionEventTestCase00(TestCase(basedistro, conf)))
  suite.addTest(ExtensionEventTestCase01(TestCase(basedistro, conf)))
  return suite


def CoreEventTestCase00(self):
  self._testMethodDoc = "Event.verify() might raise an AssertionError if --skip'd first"

  def post_setup():
    self.event.status = False
    self.clean_event_md()

  def runTest():
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
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
    self.failUnless(result.wasSuccessful(), result._strErrors())

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
    self.failUnless(result.wasSuccessful(), result._strErrors())

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
    self.failUnless(result.wasSuccessful(), result._strErrors())

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
    self.failUnless(result.wasSuccessful(), result._strErrors())

  decorate(self, 'setUp', postfn=post_setup)
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
    self.tb._unlock()
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
