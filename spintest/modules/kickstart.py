from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_extension_suite
from spintest.mixins import touch_input_files, remove_input_files

class KickstartEventTestCase(EventTestCase):
  moduleid = 'kickstart'
  eventid  = 'kickstart'
  _conf = """<kickstart>infile</kickstart>"""

  def setUp(self):
    EventTestCase.setUp(self)
    if self.event:
      touch_input_files(self.event._config.file.abspath().dirname)

  def tearDown(self):
    if self.event:
      remove_input_files(self.event._config.file.abspath().dirname)
    EventTestCase.tearDown(self)

def make_suite(basedistro):
  suite = ModuleTestSuite('kickstart')

  suite.addTest(make_extension_suite(KickstartEventTestCase, basedistro))

  return suite
