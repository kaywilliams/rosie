from dbtest        import ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import fdm_make_suite

def make_suite():
  suite = ModuleTestSuite('stage2-images')

  suite.addTest(make_core_suite('stage2-images'))
  suite.addTest(fdm_make_suite('stage2-images'))

  return suite
