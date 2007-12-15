from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class ReposEventTestCase(EventTestCase):
  moduleid = 'repos'
  eventid  = 'repos'

def make_suite():
  suite = ModuleTestSuite('repos')

  suite.addTest(make_core_suite(ReposEventTestCase))

  return suite
