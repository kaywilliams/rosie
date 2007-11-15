import unittest

from dims.img import MakeImage

from test import EventTest

from test.events.core   import make_core_suite
from test.events.mixins import BootConfigMixinTestCase

eventid = 'bootiso'

class BootisoEventTest(BootConfigMixinTestCase):
  def __init__(self, conf):
    BootConfigMixinTestCase.__init__(self, eventid, conf)
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
    self.tb.dispatch.execute(until=eventid)
    
    self.testArgs(self.image, filename='isolinux.cfg', defaults=self.do_defaults)


class Test_BootArgsDefault(BootisoEventTest):
  "default boot args and config-specified args in isolinux.cfg"
  def setUp(self):
    BootisoEventTest.setUp(self)
    self.event.config.get('boot-config').attrib['use-defaults'] = 'true'
    self.do_defaults = True

  
class Test_BootArgsNoDefault(BootisoEventTest):
  "default boot args not included"
  def setUp(self):
    BootisoEventTest.setUp(self)
    self.event.config.get('boot-config').attrib['use-defaults'] = 'false'
    self.do_defaults = False
  

class Test_BootArgsMacros(BootisoEventTest):
  "macro usage with non-default boot args"
  def setUp(self):
    BootisoEventTest.setUp(self)
    self.event.config.get('boot-config').attrib['use-defaults'] = 'false'
    self.event.config.get('boot-config/append-args').text += ' %{method} %{ks}'
    self.do_defaults = False


def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(Test_BootArgsDefault(conf))
  suite.addTest(Test_BootArgsNoDefault(conf))
  suite.addTest(Test_BootArgsMacros(conf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
