from dims import pps

from dbtest        import ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import ImageModifyMixinTestCase, imm_make_suite

class InitrdImageEventTestCase(ImageModifyMixinTestCase):
  def __init__(self, conf=None):
    ImageModifyMixinTestCase.__init__(self, 'initrd-image', conf)

  def setUp(self):
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()


class Test_Kickstart(InitrdImageEventTestCase):
  "kickstart file included"
  def setUp(self):
    InitrdImageEventTestCase.setUp(self)
    self.ksfile = self.event.config.getroot().file.abspath().dirname/'ks.cfg'
    self.ksfile.touch()
    self.kspath = pps.Path('/kickstarts/ks1.cfg')
    self.event.cvars['kickstart-file'] = self.ksfile
    self.event.cvars['ks-path'] = self.kspath

  def runTest(self):
    self.tb.dispatch.execute(until='initrd-image')
    self.check_file_in_image(self.kspath.dirname/self.ksfile.basename)

  def tearDown(self):
    InitrdImageEventTestCase.tearDown(self)
    self.ksfile.remove()


def make_suite():
  suite = ModuleTestSuite('initrd-image')

  suite.addTest(make_core_suite('initrd-image'))
  suite.addTest(imm_make_suite('initrd-image', xpath='path'))
  suite.addTest(Test_Kickstart())

  return suite
