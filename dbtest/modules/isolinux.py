from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import fdm_make_suite

class IsolinuxTestCase(EventTestCase):
  moduleid = 'isolinux'
  eventid  = 'isolinux'

def make_suite(basedistro):
  suite = ModuleTestSuite('isolinux')

  suite.addTest(make_core_suite(IsolinuxTestCase, basedistro))
  suite.addTest(fdm_make_suite(IsolinuxTestCase, basedistro))

  return suite
