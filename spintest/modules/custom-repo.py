from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class CustomRepoTestCase(EventTestCase):
  moduleid = 'custom-repo'
  eventid  = 'custom-repo'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('custom-repo')

  suite.addTest(make_core_suite(CustomRepoTestCase, basedistro, arch))

  return suite
