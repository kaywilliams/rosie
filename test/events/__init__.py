import unittest

from dims import pps

from test import EventTestCase, TestBuild, EventTestRunner, EventTestCaseDummy

class EventTestCaseHeader(EventTestCaseDummy):
  separator1 = '=' * 70
  separator2 = '-' * 70
  def __init__(self, eventid):
    self.eventid = eventid
    EventTestCaseDummy.__init__(self)
  
  def shortDescription(self):
    return '\n'.join(['', self.separator1,
                      "testing event '%s'" % self.eventid, self.separator2])

class CoreEventTestCase(EventTestCase):
  pass

class CoreEventTestCase00(CoreEventTestCase):
  "Event.verify() might raise an AssertionError if --skip'd first"
  def __init__(self, eventid, conf):
    CoreEventTestCase.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTestCase.setUp(self)
    self.event.status = False
    self.clean_event_md()
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    if self.event.diff.handlers.has_key('output'):
      self.failIf(self.event.verifier.unittest().wasSuccessful())

class CoreEventTestCase01(CoreEventTestCase):
  "Event.run() executes if neither --force nor --skip specified"
  def __init__(self, eventid, conf):
    CoreEventTestCase.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTestCase.setUp(self)
    self.event.status = None
    self.clean_event_md()
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), result._strErrors())

class CoreEventTestCase02(CoreEventTestCase):
  "Event.run() does not execute after a successful run"
  def __init__(self, eventid, conf):
    CoreEventTestCase.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTestCase.setUp(self)
    self.event.status = None
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), result._strErrors())

class CoreEventTestCase03(CoreEventTestCase):
  "Event.run() executes with --force"
  def __init__(self, eventid, conf):
    CoreEventTestCase.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTestCase.setUp(self)
    self.event.status = True
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), result._strErrors())

class CoreEventTestCase04(CoreEventTestCase):
  "Event.run() does not execute with --skip"
  def __init__(self, eventid, conf):
    CoreEventTestCase.__init__(self, eventid, conf)
  
  def setUp(self):
    CoreEventTestCase.setUp(self)
    self.event.status = False
  
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failIfRuns(self.event)
    result = self.event.verifier.unittest()
    self.failUnless(result.wasSuccessful(), result._strErrors())


class ExtensionEventTestCase(EventTestCase):
  def setUp(self):
    self.tb = TestBuild(self.conf, self.options, self.parser)
    # do not try to set up self.event cuz it may not exist

class ExtensionEventTestCase00(ExtensionEventTestCase):
  "disabling module removes output"
  def setUp(self):
    self.options.disabled_modules.append(self.eventid)
    ExtensionEventTestCase.setUp(self)
  
  def runTest(self):
    self.tb.dispatch.execute(until='autoclean')
    self.failIfExists(self.tb.dispatch._top.METADATA_DIR/self.eventid)

class ExtensionEventTestCase01(ExtensionEventTestCase):
  "renabling module regenerates output"
  def setUp(self):
    self.options.disabled_modules.remove(self.eventid)
    ExtensionEventTestCase.setUp(self)
  
  def runTest(self):
    self.failUnlessExists(self.tb.dispatch._top.METADATA_DIR/self.eventid)

def make_core_suite(eventid, conf):
  suite = unittest.TestSuite()
  suite.addTest(EventTestCaseHeader(eventid)) # hack to get a pretty header
  suite.addTest(CoreEventTestCase00(eventid, conf))
  suite.addTest(CoreEventTestCase01(eventid, conf))
  suite.addTest(CoreEventTestCase02(eventid, conf))
  suite.addTest(CoreEventTestCase03(eventid, conf))
  suite.addTest(CoreEventTestCase04(eventid, conf))
  return suite

def make_extension_suite(eventid, conf):
  suite = unittest.TestSuite()
  suite.addTest(ExtensionEventTestCase00(eventid, conf))
  suite.addTest(ExtensionEventTestCase01(eventid, conf))
  return suite


def main():
  import imp
  
  #runner = unittest.TextTestRunner(verbosity=2)
  runner = EventTestRunner()
  suite = unittest.TestSuite()
  
  for event in pps.Path('.').findpaths(mindepth=1, maxdepth=1, type=pps.constants.TYPE_DIR):
    fp = None
    try:
      try:
        fp,p,d = imp.find_module(event.basename, [event.dirname])
      except ImportError:
        continue
      mod = imp.load_module('test-%s' % event.basename, fp, p, d)
    finally:
      fp and fp.close()
    
    mod.main(suite=suite)
    del mod
  
  runner.run(suite)

if __name__ == '__main__':
  # test everything
  main()
