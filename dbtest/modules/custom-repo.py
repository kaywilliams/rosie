from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class CustomRepoTestCase(EventTestCase):
  moduleid = 'custom-repo'
  eventid  = 'custom-repo'

def make_suite():
  suite = ModuleTestSuite('custom-repo')

  suite.addTest(make_core_suite(CustomRepoTestCase))

  return suite
