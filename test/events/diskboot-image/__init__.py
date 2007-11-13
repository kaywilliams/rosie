import copy
import unittest

from test import EventTest

from test.events.core import make_suite as core_make_suite
from test.events.mixins import (ImageModifyMixinTestCase, imm_make_suite,
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
  "default boot args and config-specified args in syslinux.cfg"
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
      self.check_boot_args(labels, self.event.bootconfig._expand_macros(
        self.event.config.get('boot-config/append-args/text()', '')).split())
    finally:
      self.event.image.close()

class Test_BootArgsNoDefault(DiskbootImageEventTest):
  "macro usage with non-default boot args"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.event.image.open()
    try:
      labels = self.get_boot_args(self.event.image.list().fnmatch('syslinux.cfg')[0])
      self.check_boot_args(labels, self.event.bootconfig._expand_macros(
        self.event.config.get('boot-config/append-args/text()', '')).split())
    finally:
      self.event.image.close()


def make_suite(confdir):
  dconf = confdir/'default.conf'
  ndconf = confdir/'nodefault.conf'
  
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, dconf))
  suite.addTest(imm_make_suite(eventid, dconf, 'path'))
  suite.addTest(Test_CvarContent(dconf))
  suite.addTest(Test_BootArgsDefault(dconf))
  suite.addTest(Test_BootArgsNoDefault(ndconf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
