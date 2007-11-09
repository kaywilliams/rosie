import unittest

from origin import EventTest

class CoreEventTest00(EventTest):
  "Event.verify() raises an AssertionError if --skip'd first"
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    EventTest.setUp(self)
    self.event.status = False
    self.clean_event_md()
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    self.failIf(self.event._run)
    if self.event.provides:
      self.failUnless(not self.event.verifier.unittest().wasSuccessful())

class CoreEventTest01(EventTest):
  "Event.run() executes if neither --force nor --skip specified"
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    EventTest.setUp(self)
    self.event.status = None
    self.clean_event_md()
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless(self.event._run)
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class CoreEventTest02(EventTest):
  "Event.run() does not execute after a successful run"
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    EventTest.setUp(self)
    self.event.status = None
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    self.failIf(self.event._run)
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class CoreEventTest03(EventTest):
  "Event.run() executes with --force"
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    EventTest.setUp(self)
    self.event.status = True
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless(self.event._run)
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class CoreEventTest04(EventTest):
  "Event.run() does not execute with --skip"
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    EventTest.setUp(self)
    self.event.status = False
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    self.failIf(self.event._run)
    self.failUnless(self.event.verifier.unittest().wasSuccessful())


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
