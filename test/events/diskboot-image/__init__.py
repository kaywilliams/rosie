import copy
import unittest

from origin import EventTest

from origin.events.core import make_suite as core_make_suite
from origin.events.mixins import (ImageModifyMixinTestCase, imm_make_suite,
                                  BootConfigMixinTestCase)

eventid = 'diskboot-image'

class DiskbootImageEventTest(ImageModifyMixinTestCase, BootConfigMixinTestCase):
  def __init__(self, conf):
    ImageModifyMixinTestCase.__init__(self, eventid, conf)
    
    self.default_args = ['nousbstorage']
  
  def setUp(self):
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()
  
  
class Test_CvarContent(DiskbootImageEventTest):
  "cvars['installer-splash'], cvars['isolinux-files'] included"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.check_file_in_image(self.event.cvars['installer-splash'].basename)
    self.check_file_in_image(self.event.cvars['isolinux-files']['initrd.img'].basename)

class Test_BootArgsDefault(DiskbootImageEventTest):
  "default boot args in syslinux.cfg"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    args = self.default_args
    self._append_method_arg(args)
    self._append_ks_arg(args)
    self._append_config_args(args)
    
    self.event.image.open()
    try:
      labels = self.get_boot_args(self.event.image.list().fnmatch('syslinux.cfg')[0])
      self.check_boot_args(labels, self.default_args)
    finally:
      self.event.image.close()


def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, conf))
  suite.addTest(imm_make_suite(eventid, conf, 'path'))
  #suite.addTest(bcm_make_suite(eventid, conf))
  suite.addTest(Test_CvarContent(conf))
  suite.addTest(Test_BootArgsDefault(conf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
