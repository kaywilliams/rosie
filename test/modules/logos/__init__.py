import unittest

from dims import pps
from dims import xmllib

from test      import EventTestCase
from test.core import make_core_suite

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
  confdir = pps.Path(__file__).dirname
  suite = unittest.TestSuite()

  suite.addTest(make_core_suite('logos', confdir/'fedora6.conf'))

  suite.addTest(Test_LogosEvent_Default(confdir/'fedora6.conf'))
  suite.addTest(Test_LogosEvent_Default(confdir/'fedora7.conf'))
  suite.addTest(Test_LogosEvent_Default(confdir/'fedora8.conf'))
  suite.addTest(Test_LogosEvent_Default(confdir/'centos5.conf'))
  suite.addTest(Test_LogosEvent_Default(confdir/'redhat5.conf'))

  suite.addTest(Test_LogosEvent_Custom(confdir/'fedora6.conf'))
  suite.addTest(Test_LogosEvent_Custom(confdir/'fedora7.conf'))
  suite.addTest(Test_LogosEvent_Custom(confdir/'fedora8.conf'))
  suite.addTest(Test_LogosEvent_Custom(confdir/'centos5.conf'))
  suite.addTest(Test_LogosEvent_Custom(confdir/'redhat5.conf'))

  return suite
