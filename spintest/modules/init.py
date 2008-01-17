from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

#------ init ------#
class InitEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'init'

#------ setup ------#
class SetupEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'setup'

#------ os ------#
class OSEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'os'


def make_suite(basedistro, arch):
  suite = ModuleTestSuite('init')

  # init
  suite.addTest(make_core_suite(InitEventTestCase, basedistro, arch))

  # setup
  suite.addTest(make_core_suite(SetupEventTestCase, basedistro, arch))

  # os
  suite.addTest(make_core_suite(OSEventTestCase, basedistro, arch))

  return suite
