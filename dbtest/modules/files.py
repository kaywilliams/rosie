from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class CustomRepoTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'files', conf)

def make_suite():
  suite = ModuleTestSuite('files')

  suite.addTest(make_core_suite('files'))

  return suite
