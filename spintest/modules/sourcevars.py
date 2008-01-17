from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class SourceVarsEventTestCase(EventTestCase):
  moduleid = 'sourcevars'
  eventid  = 'source-vars'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('sourcevars')

  suite.addTest(make_core_suite(SourceVarsEventTestCase, basedistro, arch))

  return suite
