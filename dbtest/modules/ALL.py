from dbtest      import ModuleTestSuite
from dbtest.core import make_core_suite

def make_suite():
  suite = ModuleTestSuite('ALL')
  suite.addTest(make_core_suite('ALL'))

  return suite
