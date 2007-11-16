import unittest

from dims import pps

from test        import EventTestCase, EventTestRunner
from test.core   import make_core_suite
from test.mixins import ImageModifyMixinTestCase, imm_make_suite

eventid = 'initrd-image'

class InitrdImageEventTestCase(ImageModifyMixinTestCase):
  def __init__(self, conf):
    ImageModifyMixinTestCase.__init__(self, eventid, conf)
  
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
    self.tb.dispatch.execute(until=eventid)
    self.check_file_in_image(self.kspath.dirname/self.ksfile.basename)
  
  def tearDown(self):
    InitrdImageEventTestCase.tearDown(self)
    self.ksfile.remove()


def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(imm_make_suite(eventid, conf, 'path'))
  suite.addTest(Test_Kickstart(conf))
  return suite

def main(suite=None):
  import dims.pps
  config = dims.pps.Path(__file__).dirname/'%s.conf' % eventid
  if suite:
    suite.addTest(make_suite(config))
  else:
    EventTestRunner().run(make_suite(config))


if __name__ == '__main__':
  main()
