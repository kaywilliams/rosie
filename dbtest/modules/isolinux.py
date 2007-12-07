from dbtest        import ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import fdm_make_suite

def make_suite():
  suite = ModuleTestSuite('isolinux')

  suite.addTest(make_core_suite('isolinux'))
  suite.addTest(fdm_make_suite('isolinux'))

  return suite
