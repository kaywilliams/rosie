from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class ComposeTestCase(EventTestCase):
  moduleid = 'compose'
  eventid  = 'compose'


def make_suite(basedistro, arch):
  suite = ModuleTestSuite('compose')

  suite.addTest(make_core_suite(ComposeTestCase, basedistro, arch))

  return suite
