from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class AllEventTestCase(EventTestCase):
  moduleid = 'ALL'
  eventid  = 'ALL'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('ALL')
  suite.addTest(make_core_suite(AllEventTestCase, basedistro, arch))

  return suite
