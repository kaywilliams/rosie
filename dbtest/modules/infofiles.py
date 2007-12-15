from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class BuildstampEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'buildstamp'

class DiscinfoEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'discinfo'

class TreeinfoEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'treeinfo'

def make_suite():
  suite = ModuleTestSuite('infofiles')

  # buildstamp
  suite.addTest(make_core_suite(BuildstampEventTestCase))

  # discinfo
  suite.addTest(make_core_suite(DiscinfoEventTestCase))

  # treeinfo
  suite.addTest(make_core_suite(TreeinfoEventTestCase))

  return suite
