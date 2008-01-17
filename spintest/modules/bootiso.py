from rendition     import pps
from rendition.img import MakeImage

from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_core_suite
from spintest.mixins import BootConfigMixinTestCase

class BootisoEventTestCase(EventTestCase):
  moduleid = 'bootiso'
  eventid  = 'bootiso'

class _BootisoEventTestCase(BootConfigMixinTestCase, BootisoEventTestCase):
  def __init__(self, basedistro, arch, conf=None):
    EventTestCase.__init__(self, basedistro, arch, conf)
    self.default_args = []
    self.image = None
    self.do_defaults = True

  def setUp(self):
    BootisoEventTestCase.setUp(self)
    self.image = MakeImage(self.event.bootiso, 'iso')
    self._append_method_arg(self.default_args)
    self._append_ks_arg(self.default_args)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='bootiso')

    self.testArgs(self.image, filename='isolinux.cfg', defaults=self.do_defaults)


class Test_BootArgsDefault(_BootisoEventTestCase):
  "default boot args and config-specified args in isolinux.cfg"
  _conf = \
  """<bootiso>
    <boot-config use-defaults="true">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </bootiso>"""

  def setUp(self):
    _BootisoEventTestCase.setUp(self)
    self.do_defaults = True


class Test_BootArgsNoDefault(_BootisoEventTestCase):
  "default boot args not included"
  _conf = \
  """<bootiso>
    <boot-config use-defaults="false">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </bootiso>"""

  def setUp(self):
    _BootisoEventTestCase.setUp(self)
    self.event.config.get('boot-config').attrib['use-defaults'] = 'false'
    self.do_defaults = False


class Test_BootArgsMacros(_BootisoEventTestCase):
  "macro usage with non-default boot args"
  _conf = \
  """<bootiso>
    <boot-config use-defaults="false">
      <append-args>ro root=LABEL=/ %{method} %{ks}</append-args>
    </boot-config>
  </bootiso>"""

  def setUp(self):
    _BootisoEventTestCase.setUp(self)
    self.do_defaults = False


def make_suite(basedistro, arch):
  suite = ModuleTestSuite('bootiso')

  # bootiso
  suite.addTest(make_core_suite(BootisoEventTestCase, basedistro, arch))
  suite.addTest(Test_BootArgsDefault(basedistro, arch))
  suite.addTest(Test_BootArgsNoDefault(basedistro, arch))
  suite.addTest(Test_BootArgsMacros(basedistro, arch))

  return suite
