from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class InstallerEventTestCase(EventTestCase):
  moduleid = 'installer'
  eventid  = 'installer'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('installer')

  suite.addTest(make_core_suite(InstallerEventTestCase, basedistro, arch))

  return suite
