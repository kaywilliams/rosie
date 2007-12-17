from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class SoftwareEventTestCase(EventTestCase):
  moduleid = 'software'
  eventid  = 'software'

def make_suite(basedistro):
  suite = ModuleTestSuite('software')

  suite.addTest(make_core_suite(SoftwareEventTestCase, basedistro))

  return suite
