from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class ReposEventTestCase(EventTestCase):
  moduleid = 'repos'
  eventid  = 'repos'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('repos')

  suite.addTest(make_core_suite(ReposEventTestCase, basedistro, arch))

  return suite
