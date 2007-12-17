from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class RpmsTestCase(EventTestCase):
  moduleid = 'rpms'
  eventid  = 'rpms'

def make_suite(basedistro):
  suite = ModuleTestSuite('rpms')

  suite.addTest(make_core_suite(RpmsTestCase, basedistro))

  return suite
