from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class PxebootImagesEventTestCase(EventTestCase):
  moduleid = 'pxeboot-images'
  eventid  = 'pxeboot-images'

def make_suite(basedistro):
  suite = ModuleTestSuite('pxeboot-images')

  suite.addTest(make_core_suite(PxebootImagesEventTestCase, basedistro))

  return suite
