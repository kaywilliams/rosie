from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class SoftwareEventTestCase(EventTestCase):
  moduleid = 'software'
  eventid  = 'software'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('software')

  suite.addTest(make_core_suite(SoftwareEventTestCase, basedistro, arch))

  return suite
