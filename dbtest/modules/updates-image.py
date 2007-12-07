from dbtest        import ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import ImageModifyMixinTestCase, imm_make_suite

def make_suite():
  suite = ModuleTestSuite('updates-image')

  suite.addTest(make_core_suite('updates-image'))
  suite.addTest(imm_make_suite('updates-image', xpath='path'))

  return suite
