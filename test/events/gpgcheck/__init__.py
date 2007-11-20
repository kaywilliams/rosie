import unittest

from test import EventTestCase, EventTestRunner
from test.core import make_core_suite

eventid = 'gpgcheck'

class Test_GpgKeysNotProvided(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, eventid, conf)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)

def make_suite(confdir):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(confdir / 'keys-present.conf'))
  suite.addTest(Test_GpgKeysNotProvided(confdir / 'keys-missing.conf'))
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


