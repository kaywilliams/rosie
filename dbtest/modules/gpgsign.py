from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class CustomRepoTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'gpgsign', conf)

def make_suite():
  suite = ModuleTestSuite('gpgsign')

  suite.addTest(make_core_suite('gpgsign'))

  return suite
