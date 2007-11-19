import unittest

from dims import xmllib

from test import EventTestCase, EventTestRunner, EventTestResult
from test.core import make_core_suite

eventid = 'release-files'

class Test_ReleaseEvent_Default(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, eventid, conf)

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('release-rpm', self.event._config, attrs={'enabled': 'False'})

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseEvent_Custom(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, eventid, conf)

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('release-rpm', self.event._config, attrs={'enabled': 'True'})

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite(confdir):
  suite = unittest.TestSuite()

  #suite.addTest(make_core_suite(eventid, confdir/'fedora6.conf'))

  suite.addTest(Test_ReleaseEvent_Default(confdir/'fedora6.conf'))
  suite.addTest(Test_ReleaseEvent_Default(confdir/'fedora7.conf'))
  suite.addTest(Test_ReleaseEvent_Default(confdir/'fedora8.conf'))
  suite.addTest(Test_ReleaseEvent_Default(confdir/'centos5.conf'))
  suite.addTest(Test_ReleaseEvent_Default(confdir/'redhat5.conf'))

  suite.addTest(Test_ReleaseEvent_Custom(confdir/'fedora6.conf'))
  suite.addTest(Test_ReleaseEvent_Custom(confdir/'fedora7.conf'))
  suite.addTest(Test_ReleaseEvent_Custom(confdir/'fedora8.conf'))
  suite.addTest(Test_ReleaseEvent_Custom(confdir/'centos5.conf'))
  suite.addTest(Test_ReleaseEvent_Custom(confdir/'redhat5.conf'))

  return suite

def main(suite=None):
  import dims.pps
  confdir = dims.pps.Path(__file__).dirname
  if suite:
    suite.addTest(make_suite(confdir))
  else:
    EventTestRunner().run(make_suite(confdir))

if __name__ == '__main__':
  main()

