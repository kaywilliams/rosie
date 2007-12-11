from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class ComposeTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'compose', conf)

def make_suite():
  suite = ModuleTestSuite('compose')

  suite.addTest(make_core_suite('compose'))

  return suite
