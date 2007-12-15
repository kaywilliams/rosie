from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import fdm_make_suite

class Stage2ImagesEventTestCase(EventTestCase):
  moduleid = 'stage2-images'
  eventid  = 'stage2-images'

def make_suite():
  suite = ModuleTestSuite('stage2-images')

  suite.addTest(make_core_suite(Stage2ImagesEventTestCase))
  suite.addTest(fdm_make_suite(Stage2ImagesEventTestCase))

  return suite
