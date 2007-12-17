from dims import pps

from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import ImageModifyMixinTestCase, imm_make_suite

class InitrdImageEventTestCase(EventTestCase):
  moduleid = 'initrd-image'
  eventid  = 'initrd-image'

class _InitrdImageEventTestCase(ImageModifyMixinTestCase,
                                InitrdImageEventTestCase):
  def __init__(self, basedistro, conf=None):
    ImageModifyMixinTestCase.__init__(self)
    InitrdImageEventTestCase.__init__(self, basedistro, conf)

  def setUp(self):
    InitrdImageEventTestCase.setUp(self)
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    ImageModifyMixinTestCase.tearDown(self)
    InitrdImageEventTestCase.tearDown(self)


class Test_Kickstart(_InitrdImageEventTestCase):
  "kickstart file included"
  def setUp(self):
    _InitrdImageEventTestCase.setUp(self)
    self.ksfile = self.event.config.getroot().file.abspath().dirname/'ks.cfg'
    self.ksfile.touch()
    self.kspath = pps.Path('/kickstarts/ks1.cfg')
    self.event.cvars['kickstart-file'] = self.ksfile
    self.event.cvars['ks-path'] = self.kspath

  def runTest(self):
    self.tb.dispatch.execute(until='initrd-image')
    self.check_file_in_image(self.kspath.dirname/self.ksfile.basename)

  def tearDown(self):
    _InitrdImageEventTestCase.tearDown(self)
    self.ksfile.remove()


def make_suite(basedistro):
  suite = ModuleTestSuite('initrd-image')

  suite.addTest(make_core_suite(InitrdImageEventTestCase, basedistro))
  suite.addTest(imm_make_suite(_InitrdImageEventTestCase, basedistro, xpath='path'))
  suite.addTest(Test_Kickstart(basedistro))

  return suite
