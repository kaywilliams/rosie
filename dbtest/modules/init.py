from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

#------ init ------#
class InitEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'init'

#------ setup ------#
class SetupEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'setup'

#------ OS ------#
class OSEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'OS'


def make_suite():
  suite = ModuleTestSuite('init')

  # init
  suite.addTest(make_core_suite(InitEventTestCase))

  # setup
  suite.addTest(make_core_suite(SetupEventTestCase))

  # OS
  suite.addTest(make_core_suite(OSEventTestCase))

  return suite
