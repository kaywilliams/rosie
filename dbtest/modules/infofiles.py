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

def make_suite(basedistro):
  suite = ModuleTestSuite('infofiles')

  # buildstamp
  suite.addTest(make_core_suite(BuildstampEventTestCase, basedistro))

  # discinfo
  suite.addTest(make_core_suite(DiscinfoEventTestCase, basedistro))

  # treeinfo
  suite.addTest(make_core_suite(TreeinfoEventTestCase, basedistro))

  return suite
