from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class CustomRepoTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'custom-repo', conf)

def make_suite():
  suite = ModuleTestSuite('custom-repo')

  suite.addTest(make_core_suite('custom-repo'))

  return suite
