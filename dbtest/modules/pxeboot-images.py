from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class PxebootImagesTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'pxeboot-images', conf)

def make_suite():
  suite = ModuleTestSuite('pxeboot-images')

  suite.addTest(make_core_suite('pxeboot-images'))

  return suite
