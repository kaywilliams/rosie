from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class AllEventTestCase(EventTestCase):
  moduleid = 'all'
  eventid  = 'all'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('all')
  suite.addTest(make_core_suite(AllEventTestCase, basedistro, arch))

  return suite
