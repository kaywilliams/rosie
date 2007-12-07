from dbtest      import ModuleTestSuite
from dbtest.core import make_core_suite

def make_suite():
  suite = ModuleTestSuite('publish')

  # publish-setup
  suite.addTest(make_core_suite('publish-setup'))

  #publish

  return suite
