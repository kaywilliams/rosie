from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

def make_suite():
  suite = ModuleTestSuite('installer')

  suite.addTest(make_core_suite('installer'))

  return suite
