import unittest

from test import EventTest

from test.events.core import make_suite as core_make_suite

eventid = 'autoclean'
non_meta_event = 'comps'
meta_event = 'setup'

class AutocleanEventTest(EventTest):
  pass

class AutocleanEventTest10(AutocleanEventTest):
  "standard run (non-meta events)"
  def __init__(self, conf):
    AutocleanEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 0
    
    self.clean_event_md(self.non_meta_event)
    self.clean_event_md()
  
  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failUnlessRuns(self.non_meta_event)

class AutocleanEventTest11(AutocleanEventTest):
  "Event.run() executes on Event.event_version change"
  def __init__(self, conf):
    AutocleanEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 1
    
  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failUnlessRuns(self.non_meta_event)

class AutocleanEventTest12(AutocleanEventTest):
  "Event.run() does not execute when Event.event_version unchanged"
  def __init__(self, conf):
    AutocleanEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 1
    
  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failIfRuns(self.non_meta_event)

class AutocleanEventTest13(AutocleanEventTest):
  "standard run (meta events)"
  def __init__(self, conf):
    AutocleanEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    AutocleanEventTest.setUp(self)
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

class AutocleanEventTest14(AutocleanEventTest):
  "Event.run() executes on Event.event_version change (and all children)"
  def __init__(self, conf):
    AutocleanEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.meta_event = self.event._getroot().get(meta_event)
    self.meta_event.event_version = 1
  
  def runTest(self):
    self.execute_predecessors(self.meta_event)
    for event in [self.meta_event] + self.meta_event.get_children():
      self.failUnlessRuns(event)

class AutocleanEventTest15(AutocleanEventTest):
  "Event.run() does not execute when Event.event_version unchanged (and all children)"
  def __init__(self, conf):
    AutocleanEventTest.__init__(self, eventid, conf)
  
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.meta_event = self.event._getroot().get(meta_event)
    self.meta_event.event_version = 1
  
  def runTest(self):
    self.execute_predecessors(self.meta_event)
    for event in [self.meta_event] + self.meta_event.get_children():
      self.failIfRuns(event)


def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, conf))
  suite.addTest(AutocleanEventTest10(conf))
  suite.addTest(AutocleanEventTest11(conf))
  suite.addTest(AutocleanEventTest12(conf))
  suite.addTest(AutocleanEventTest13(conf))
  suite.addTest(AutocleanEventTest14(conf))
  suite.addTest(AutocleanEventTest15(conf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)
  

if __name__ == '__main__':
  main()
