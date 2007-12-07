from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class SoftwareTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'software', conf)

def make_suite():
  suite = ModuleTestSuite('software')

  suite.addTest(make_core_suite('software'))

  return suite
