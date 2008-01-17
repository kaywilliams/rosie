from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class RpmsTestCase(EventTestCase):
  moduleid = 'rpms'
  eventid  = 'rpms'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('rpms')

  suite.addTest(make_core_suite(RpmsTestCase, basedistro, arch))

  return suite
