from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class BuildstampEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'buildstamp'

class DiscinfoEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'discinfo'

class TreeinfoEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'treeinfo'

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('infofiles')

  # buildstamp
  suite.addTest(make_core_suite(BuildstampEventTestCase, basedistro, arch))

  # discinfo
  suite.addTest(make_core_suite(DiscinfoEventTestCase, basedistro, arch))

  # treeinfo
  suite.addTest(make_core_suite(TreeinfoEventTestCase, basedistro, arch))

  return suite
