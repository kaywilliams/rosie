from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class ComposeTestCase(EventTestCase):
  moduleid = 'compose'
  eventid  = 'compose'


def make_suite(basedistro):
  suite = ModuleTestSuite('compose')

  suite.addTest(make_core_suite(ComposeTestCase, basedistro))

  return suite
