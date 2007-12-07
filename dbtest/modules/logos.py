from dims import pps
from dims import xmllib

from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.config import make_default_config
from dbtest.core   import make_core_suite

class Test_LogosEvent_Default(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'logos', conf)

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('logos-rpm', self.event._config, attrs={'enabled': 'False'})

  def runTest(self):
    self.tb.dispatch.execute(until='logos')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosEvent_Custom(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'logos', conf)

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('logos-rpm', self.event._config, attrs={'enabled': 'True'})

  def runTest(self):
    self.tb.dispatch.execute(until='logos')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite():
  suite = ModuleTestSuite('logos')

  suite.addTest(make_core_suite('logos', make_default_config('logos')))

  suite.addTest(Test_LogosEvent_Default(make_default_config('logos', 'fedora-6')))
  suite.addTest(Test_LogosEvent_Default(make_default_config('logos', 'fedora-7')))
  suite.addTest(Test_LogosEvent_Default(make_default_config('logos', 'fedora-8')))
  suite.addTest(Test_LogosEvent_Default(make_default_config('logos', 'centos-5')))
  suite.addTest(Test_LogosEvent_Default(make_default_config('logos', 'redhat-5')))

  suite.addTest(Test_LogosEvent_Custom(make_default_config('logos', 'fedora-6')))
  suite.addTest(Test_LogosEvent_Custom(make_default_config('logos', 'fedora-7')))
  suite.addTest(Test_LogosEvent_Custom(make_default_config('logos', 'fedora-8')))
  suite.addTest(Test_LogosEvent_Custom(make_default_config('logos', 'centos-5')))
  suite.addTest(Test_LogosEvent_Custom(make_default_config('logos', 'redhat-5')))

  return suite
