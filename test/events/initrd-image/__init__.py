import unittest

from dims import pps

from test import EventTest

from test.events.core   import make_core_suite
from test.events.mixins import ImageModifyMixinTestCase, imm_make_suite

eventid = 'initrd-image'

class InitrdImageEventTest(ImageModifyMixinTestCase):
  def __init__(self, conf):
    ImageModifyMixinTestCase.__init__(self, eventid, conf)
  
  def setUp(self):
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()
  
  
class Test_Kickstart(InitrdImageEventTest):
  "kickstart file included"
  def setUp(self):
    InitrdImageEventTest.setUp(self)
    self.ksfile = self.event.config.getroot().file.abspath().dirname/'ks.cfg'
    self.ksfile.touch()
    self.kspath = pps.Path('/kickstarts/ks1.cfg')
    self.event.cvars['kickstart-file'] = self.ksfile
    self.event.cvars['ks-path'] = self.kspath
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_file_in_image(self.kspath.dirname/self.ksfile.basename)
  
  def tearDown(self):
    InitrdImageEventTest.tearDown(self)
    self.ksfile.remove()


def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(imm_make_suite(eventid, conf, 'path'))
  suite.addTest(Test_Kickstart(conf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
