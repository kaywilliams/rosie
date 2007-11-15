import unittest

from test import EventTest

from test.events.core import make_core_suite

eventid = 'autoclean'
non_meta_event = 'comps'
meta_event = 'setup'

class AutocleanEventTest(EventTest):
  def __init__(self, conf):
    EventTest.__init__(self, eventid, conf)

class Test_NonMeta(AutocleanEventTest):
  "standard run (non-meta events)"
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 0
    
    self.clean_event_md(self.non_meta_event)
    self.clean_event_md()
  
  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failUnlessRuns(self.non_meta_event)

class Test_NonMetaVersion(AutocleanEventTest):
  "Event.run() executes on Event.event_version change"
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 1
    
  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failUnlessRuns(self.non_meta_event)

class Test_NonMetaNoVersion(AutocleanEventTest):
  "Event.run() does not execute when Event.event_version unchanged"
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.non_meta_event = self.event._getroot().get(non_meta_event)
    self.non_meta_event.event_version = 1
    
  def runTest(self):
    self.execute_predecessors(self.non_meta_event)
    self.failIfRuns(self.non_meta_event)

class Test_Meta(AutocleanEventTest):
  "standard run (meta events)"
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

class Test_MetaVersion(AutocleanEventTest):
  "Event.run() executes on Event.event_version change (and all children)"
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.meta_event = self.event._getroot().get(meta_event)
    self.meta_event.event_version = 1
  
  def runTest(self):
    self.execute_predecessors(self.meta_event)
    for event in [self.meta_event] + self.meta_event.get_children():
      self.failUnlessRuns(event)

class Test_MetaNoVersion(AutocleanEventTest):
  "Event.run() does not execute when Event.event_version unchanged (and all children)"
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.meta_event = self.event._getroot().get(meta_event)
    self.meta_event.event_version = 1
  
  def runTest(self):
    self.execute_predecessors(self.meta_event)
    for event in [self.meta_event] + self.meta_event.get_children():
      self.failIfRuns(event)

class Test_RemoveDisabled(AutocleanEventTest):
  "remove disabled event directories"
  def setUp(self):
    AutocleanEventTest.setUp(self)
    self.test_dir = self.event.METADATA_DIR/'test_disabled_event'
    self.test_dir.mkdirs()
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failIfExists(self.test_dir)
  
  def tearDown(self):
    if self.test_dir.exists(): self.test_dir.remove()


def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(Test_NonMeta(conf))
  suite.addTest(Test_NonMetaVersion(conf))
  suite.addTest(Test_NonMetaNoVersion(conf))
  suite.addTest(Test_Meta(conf))
  suite.addTest(Test_MetaVersion(conf))
  suite.addTest(Test_MetaNoVersion(conf))
  suite.addTest(Test_RemoveDisabled(conf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)
  

if __name__ == '__main__':
  main()
