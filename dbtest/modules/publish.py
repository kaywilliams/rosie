from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class PublishSetupEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish-setup'

class PublishEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish'

# TODO - figure out a way to delete the published directories after we're done

def make_suite(basedistro):
  suite = ModuleTestSuite('publish')

  # publish-setup
  suite.addTest(make_core_suite(PublishSetupEventTestCase, basedistro))

  # publish
  suite.addTest(make_core_suite(PublishEventTestCase, basedistro))

  return suite
