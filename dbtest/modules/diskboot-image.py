from dims import pps

from dbtest        import ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import (ImageModifyMixinTestCase, imm_make_suite,
                           BootConfigMixinTestCase)

class DiskbootImageEventTestCase(ImageModifyMixinTestCase, BootConfigMixinTestCase):
  def __init__(self, conf=None):
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
  _conf = \
  """<diskboot-image>
    <boot-config>
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </diskboot-image>"""

  def runTest(self):
    self.tb.dispatch.execute(until='diskboot-image')

    self.check_file_in_image(self.event.cvars['installer-splash'].basename)
    self.check_file_in_image(self.event.cvars['isolinux-files']['initrd.img'].basename)

class Test_BootArgsDefault(DiskbootImageEventTestCase):
  "default boot args and config-specified args in syslinux.cfg"
  _conf = \
  """<diskboot-image>
    <boot-config use-defaults="true">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </diskboot-image>"""

  def setUp(self):
    DiskbootImageEventTestCase.setUp(self)
    self.do_defaults = True

class Test_BootArgsNoDefault(DiskbootImageEventTestCase):
  "default boot args not included"
  _conf = \
  """<diskboot-image>
    <boot-config use-defaults="false">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </diskboot-image>"""

  def setUp(self):
    DiskbootImageEventTestCase.setUp(self)
    self.do_defaults = False

class Test_BootArgsMacros(DiskbootImageEventTestCase):
  "macro usage with non-default boot args"
  _conf = \
  """<diskboot-image>
    <boot-config use-defaults="false">
      <append-args>ro root=LABEL=/ %{method} %{ks}</append-args>
    </boot-config>
  </diskboot-image>"""

  def setUp(self):
    DiskbootImageEventTestCase.setUp(self)
    self.do_defaults = False


def make_suite():
  suite = ModuleTestSuite('diskboot-image')

  suite.addTest(make_core_suite('diskboot-image'))
  suite.addTest(imm_make_suite('diskboot-image', xpath='path'))
  suite.addTest(Test_CvarContent())
  suite.addTest(Test_BootArgsDefault())
  suite.addTest(Test_BootArgsNoDefault())
  suite.addTest(Test_BootArgsMacros())

  return suite
