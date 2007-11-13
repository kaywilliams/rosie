import unittest

from dims.img import MakeImage

from test import EventTest

from test.events.core import make_suite as core_make_suite
from test.events.mixins import BootConfigMixinTestCase

eventid = 'bootiso'

class BootisoEventTest(BootConfigMixinTestCase):
  def __init__(self, conf):
    BootConfigMixinTestCase.__init__(self, eventid, conf)
    self.default_args = []
    self.image = None
    
  def setUp(self):
    BootConfigMixinTestCase.setUp(self)
    self.image = MakeImage(self.event.bootiso, 'iso')
    self.clean_event_md()
  
class Test_BootArgsDefault(BootisoEventTest):
  "default boot args and config-specified args in isolinux.cfg"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    args = self.default_args
    self._append_method_arg(args)
    self._append_ks_arg(args)
    self._append_config_args(args)
    
    self.image.open('r')
    try:
      labels = self.get_boot_args(self.image.list().fnmatch('isolinux.cfg')[0])
      self.check_boot_args(labels, self.default_args)
      self.check_boot_args(labels, self.event.bootconfig._expand_macros(
        self.event.config.get('boot-config/append-args/text()', '')).split())
    finally:
      self.image.close()

class Test_BootArgsNoDefault(BootisoEventTest):
  "macro usage with non-default boot args"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.image.open('r')
    try:
      labels = self.get_boot_args(self.image.list().fnmatch('isolinux.cfg')[0])
      self.check_boot_args(labels, self.event.bootconfig._expand_macros(
        self.event.config.get('boot-config/append-args/text()', '')).split())
    finally:
      self.image.close()


def make_suite(confdir):
  dconf = confdir/'default.conf'
  ndconf = confdir/'nodefault.conf'
  
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, dconf))
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
