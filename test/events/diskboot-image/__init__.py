import unittest

from test        import EventTestRunner
from test.core   import make_core_suite
from test.mixins import (ImageModifyMixinTestCase, imm_make_suite,
                         BootConfigMixinTestCase)

eventid = 'diskboot-image'

class DiskbootImageEventTestCase(ImageModifyMixinTestCase, BootConfigMixinTestCase):
  def __init__(self, conf):
    ImageModifyMixinTestCase.__init__(self, eventid, conf)
    
    self.default_args = ['nousbstorage']
    self.do_defaults = True
  
  def setUp(self):
    ImageModifyMixinTestCase.setUp(self)
    self._append_method_arg(self.default_args)
    self._append_ks_arg(self.default_args)
    self.clean_event_md()
    
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.testArgs(self.event.image, filename='syslinux.cfg', defaults=self.do_defaults)
  
  
class Test_CvarContent(DiskbootImageEventTestCase):
  "cvars['installer-splash'], cvars['isolinux-files'] included"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.check_file_in_image(self.event.cvars['installer-splash'].basename)
    self.check_file_in_image(self.event.cvars['isolinux-files']['initrd.img'].basename)

class Test_BootArgsDefault(DiskbootImageEventTestCase):
  "default boot args and config-specified args in syslinux.cfg"
  def setUp(self):
    DiskbootImageEventTestCase.setUp(self)
    self.event.config.get('boot-config').attrib['use-defaults'] = 'true'
    self.do_defaults = True
    
class Test_BootArgsNoDefault(DiskbootImageEventTestCase):
  "default boot args not included"
  def setUp(self):
    DiskbootImageEventTestCase.setUp(self)
    self.event.config.get('boot-config').attrib['use-defaults'] = 'false'
    self.do_defaults = False
  
class Test_BootArgsMacros(DiskbootImageEventTestCase):
  "macro usage with non-default boot args"
  def setUp(self):
    DiskbootImageEventTestCase.setUp(self)
    self.event.config.get('boot-config').attrib['use-defaults'] = 'false'
    self.event.config.get('boot-config/append-args').text += ' %{method} %{ks}'
    self.do_defaults = False
  

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(imm_make_suite(eventid, conf, 'path'))
  suite.addTest(Test_CvarContent(conf))
  suite.addTest(Test_BootArgsDefault(conf))
  suite.addTest(Test_BootArgsNoDefault(conf))
  suite.addTest(Test_BootArgsMacros(conf))
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
