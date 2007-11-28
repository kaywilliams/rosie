import unittest

from dims import pps

from test.core   import make_core_suite
from test.mixins import ImageModifyMixinTestCase, imm_make_suite

class InitrdImageEventTestCase(ImageModifyMixinTestCase):
  def __init__(self, conf):
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
  conf = pps.Path(__file__).dirname/'initrd-image.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('initrd-image', conf))
  suite.addTest(imm_make_suite('initrd-image', conf, 'path'))
  suite.addTest(Test_Kickstart(conf))
  
  return suite
