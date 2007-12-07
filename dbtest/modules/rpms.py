from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class RpmsTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'rpms', conf)

def make_suite():
  suite = ModuleTestSuite('rpms')

  suite.addTest(make_core_suite('rpms'))

  return suite
