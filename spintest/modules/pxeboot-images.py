from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class PxebootImagesEventTestCase(EventTestCase):
  moduleid = 'pxeboot-images'
  eventid  = 'pxeboot-images'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('pxeboot-images')

  suite.addTest(make_core_suite(PxebootImagesEventTestCase, basedistro, arch))

  return suite
