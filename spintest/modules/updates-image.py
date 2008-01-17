from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_core_suite
from spintest.mixins import ImageModifyMixinTestCase, imm_make_suite

class UpdatesImageEventTestCase(EventTestCase):
  moduleid = 'updates-image'
  eventid  = 'updates-image'

class _UpdatesImageEventTestCase(ImageModifyMixinTestCase,
                                 UpdatesImageEventTestCase):
  def __init__(self, basedistro, arch, conf=None):
    UpdatesImageEventTestCase.__init__(self, basedistro, arch, conf)
    ImageModifyMixinTestCase.__init__(self)

  def setUp(self):
    UpdatesImageEventTestCase.setUp(self)
    ImageModifyMixinTestCase.setUp(self)

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('updates-image')

  suite.addTest(make_core_suite(UpdatesImageEventTestCase, basedistro, arch))
  suite.addTest(imm_make_suite(_UpdatesImageEventTestCase, basedistro, arch, xpath='path'))

  return suite
