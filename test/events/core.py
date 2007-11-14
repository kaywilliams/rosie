import unittest

from test import EventTest

class CoreEventTest(EventTest):
  pass

class CoreEventTest00(CoreEventTest):
  "Event.verify() raises an AssertionError if --skip'd first"
  def __init__(self, eventid, conf):
    CoreEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTest.setUp(self)
    self.event.status = False
    self.clean_event_md()
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    if self.event.provides:
      result = self.event.verifier.unittest()
      self.failIf(result.wasSuccessful())

class CoreEventTest01(CoreEventTest):
  "Event.run() executes if neither --force nor --skip specified"
  def __init__(self, eventid, conf):
    CoreEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTest.setUp(self)
    self.event.status = None
    self.clean_event_md()
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), result._strErrors())

class CoreEventTest02(CoreEventTest):
  "Event.run() does not execute after a successful run"
  def __init__(self, eventid, conf):
    CoreEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTest.setUp(self)
    self.event.status = None
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), result._strErrors())

class CoreEventTest03(CoreEventTest):
  "Event.run() executes with --force"
  def __init__(self, eventid, conf):
    CoreEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTest.setUp(self)
    self.event.status = True
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), result._strErrors())

class CoreEventTest04(CoreEventTest):
  "Event.run() does not execute with --skip"
  def __init__(self, eventid, conf):
    CoreEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTest.setUp(self)
    self.event.status = False
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), result._strErrors())


def make_suite(eventid, conf):
  suite = unittest.TestSuite()
  suite.addTest(CoreEventTest00(eventid, conf))
  suite.addTest(CoreEventTest01(eventid, conf))
  suite.addTest(CoreEventTest02(eventid, conf))
  suite.addTest(CoreEventTest03(eventid, conf))
  suite.addTest(CoreEventTest04(eventid, conf))
  return suite

if __name__ == '__main__':
  eventid = 'comps'
  
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(eventid, '%s/%s.conf' % (eventid, eventid))
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)
