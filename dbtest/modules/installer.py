from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class InstallerEventTestCase(EventTestCase):
  moduleid = 'installer'
  eventid  = 'installer'

def make_suite():
  suite = ModuleTestSuite('installer')

  suite.addTest(make_core_suite(InstallerEventTestCase))

  return suite
