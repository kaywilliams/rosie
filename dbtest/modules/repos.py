from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class CustomRepoTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'repos', conf)

def make_suite():
  suite = ModuleTestSuite('repos')

  suite.addTest(make_core_suite('repos'))

  return suite
