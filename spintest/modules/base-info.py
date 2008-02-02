from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class BaseInfoEventTestCase(EventTestCase):
  moduleid = 'base-info'
  eventid  = 'base-info'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('base-info')

  suite.addTest(make_core_suite(BaseInfoEventTestCase, basedistro, arch))

  return suite
