from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class ComposeTestCase(EventTestCase):
  moduleid = 'compose'
  eventid  = 'compose'


def make_suite():
  suite = ModuleTestSuite('compose')

  suite.addTest(make_core_suite(ComposeTestCase))

  return suite
