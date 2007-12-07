from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class SourceVarsTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'source-vars', conf)

def make_suite():
  suite = ModuleTestSuite('sourcevars')

  suite.addTest(make_core_suite('source-vars'))

  return suite
