from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class SourceVarsEventTestCase(EventTestCase):
  moduleid = 'sourcevars'
  eventid  = 'source-vars'

def make_suite():
  suite = ModuleTestSuite('sourcevars')

  suite.addTest(make_core_suite(SourceVarsEventTestCase))

  return suite
