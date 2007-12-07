from dims     import pps
from dims.img import MakeImage

from dbtest        import ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import BootConfigMixinTestCase

class BootisoEventTestCase(BootConfigMixinTestCase):
  def __init__(self):
    BootConfigMixinTestCase.__init__(self, 'bootiso')
    self.default_args = []
    self.image = None
    self.do_defaults = True

  def setUp(self):
    BootConfigMixinTestCase.setUp(self)
    self.image = MakeImage(self.event.bootiso, 'iso')
    self._append_method_arg(self.default_args)
    self._append_ks_arg(self.default_args)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='bootiso')

    self.testArgs(self.image, filename='isolinux.cfg', defaults=self.do_defaults)


class Test_BootArgsDefault(BootisoEventTestCase):
  "default boot args and config-specified args in isolinux.cfg"
  _conf = \
  """<bootiso>
    <boot-config use-defaults="true">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </bootiso>"""

  def setUp(self):
    BootisoEventTestCase.setUp(self)
    self.do_defaults = True


class Test_BootArgsNoDefault(BootisoEventTestCase):
  "default boot args not included"
  _conf = \
  """<bootiso>
    <boot-config use-defaults="false">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </bootiso>"""

  def setUp(self):
    BootisoEventTestCase.setUp(self)
    self.event.config.get('boot-config').attrib['use-defaults'] = 'false'
    self.do_defaults = False


class Test_BootArgsMacros(BootisoEventTestCase):
  "macro usage with non-default boot args"
  _conf = \
  """<bootiso>
    <boot-config use-defaults="false">
      <append-args>ro root=LABEL=/ %{method} %{ks}</append-args>
    </boot-config>
  </bootiso>"""

  def setUp(self):
    BootisoEventTestCase.setUp(self)
    self.do_defaults = False


def make_suite():
  suite = ModuleTestSuite('bootiso')

  # bootiso
  suite.addTest(make_core_suite('bootiso'))
  suite.addTest(Test_BootArgsDefault())
  suite.addTest(Test_BootArgsNoDefault())
  suite.addTest(Test_BootArgsMacros())

  return suite
