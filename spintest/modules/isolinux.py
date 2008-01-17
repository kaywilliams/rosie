from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_core_suite
from spintest.mixins import fdm_make_suite

class IsolinuxTestCase(EventTestCase):
  moduleid = 'isolinux'
  eventid  = 'isolinux'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('isolinux')

  suite.addTest(make_core_suite(IsolinuxTestCase, basedistro, arch))
  suite.addTest(fdm_make_suite(IsolinuxTestCase, basedistro, arch))

  return suite
