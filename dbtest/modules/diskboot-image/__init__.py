import unittest

from dims import pps

from dbtest.core   import make_core_suite
from dbtest.mixins import (ImageModifyMixinTestCase, imm_make_suite,
                           BootConfigMixinTestCase)

class DiskbootImageEventTestCase(ImageModifyMixinTestCase, BootConfigMixinTestCase):
  def __init__(self, conf):
    ImageModifyMixinTestCase.__init__(self, 'diskboot-image', conf)

    self.default_args = ['nousbstorage']
    self.do_defaults = True

  def setUp(self):
    ImageModifyMixinTestCase.setUp(self)
    self._append_method_arg(self.default_args)
    self._append_ks_arg(self.default_args)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='diskboot-image')
    self.testArgs(self.event.image, filename='syslinux.cfg', defaults=self.do_defaults)


class Test_CvarContent(DiskbootImageEventTestCase):
  "cvars['installer-splash'], cvars['isolinux-files'] included"
  def runTest(self):
    self.tb.dispatch.execute(until='diskboot-image')

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


def make_suite():
  conf = pps.Path(__file__).dirname/'diskboot-image.conf'
  suite = unittest.TestSuite()

  suite.addTest(make_core_suite('diskboot-image', conf))
  suite.addTest(imm_make_suite('diskboot-image', conf, 'path'))
  suite.addTest(Test_CvarContent(conf))
  suite.addTest(Test_BootArgsDefault(conf))
  suite.addTest(Test_BootArgsNoDefault(conf))
  suite.addTest(Test_BootArgsMacros(conf))

  return suite
