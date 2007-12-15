from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class AllEventTestCase(EventTestCase):
  moduleid = 'ALL'
  eventid  = 'ALL'

def make_suite():
  suite = ModuleTestSuite('ALL')
  suite.addTest(make_core_suite(AllEventTestCase))

  return suite
