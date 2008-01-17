from rendition import pps
from rendition import xmllib

from spintest        import EventTestCase, ModuleTestSuite
from spintest.config import make_default_config
from spintest.core   import make_core_suite

class LogosEventTestCase(EventTestCase):
  moduleid = 'logos'
  eventid  = 'logos'

class Test_LogosEvent_Default(LogosEventTestCase):
  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('logos-rpm', self.event._config, attrs={'enabled': 'False'})

  def runTest(self):
    self.tb.dispatch.execute(until='logos')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosEvent_Custom(LogosEventTestCase):
  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('logos-rpm', self.event._config, attrs={'enabled': 'True'})

  def runTest(self):
    self.tb.dispatch.execute(until='logos')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('logos')

  suite.addTest(make_core_suite(LogosEventTestCase, basedistro, arch))
  suite.addTest(Test_LogosEvent_Default(basedistro, arch))
  suite.addTest(Test_LogosEvent_Custom(basedistro, arch))

  return suite
