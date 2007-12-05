import unittest

from dims import pps

from dbtest      import EventTestCase
from dbtest.core import make_core_suite

class Test_GpgKeysNotProvided(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'gpgcheck', conf)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)

def make_suite():
  confdir = pps.Path(__file__).dirname
  suite = unittest.TestSuite()

  suite.addTest(make_core_suite('gpgcheck', confdir / 'keys-present.conf'))
  suite.addTest(Test_GpgKeysNotProvided(confdir / 'keys-missing.conf'))

  return suite
