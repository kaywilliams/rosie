from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import ImageModifyMixinTestCase, imm_make_suite

class UpdatesImageEventTestCase(EventTestCase):
  moduleid = 'updates-image'
  eventid  = 'updates-image'

class _UpdatesImageEventTestCase(ImageModifyMixinTestCase,
                                 UpdatesImageEventTestCase):
  def __init__(self, conf=None):
    UpdatesImageEventTestCase.__init__(self, conf)
    ImageModifyMixinTestCase.__init__(self)

  def setUp(self):
    UpdatesImageEventTestCase.setUp(self)
    ImageModifyMixinTestCase.setUp(self)

def make_suite():
  suite = ModuleTestSuite('updates-image')

  suite.addTest(make_core_suite(UpdatesImageEventTestCase))
  suite.addTest(imm_make_suite(_UpdatesImageEventTestCase, xpath='path'))

  return suite
