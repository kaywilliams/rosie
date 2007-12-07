from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

def make_suite():
  suite = ModuleTestSuite('infofiles')

  # buildstamp
  suite.addTest(make_core_suite('buildstamp'))

  # discinfo
  suite.addTest(make_core_suite('discinfo'))

  # treeinfo
  suite.addTest(make_core_suite('treeinfo'))

  return suite
