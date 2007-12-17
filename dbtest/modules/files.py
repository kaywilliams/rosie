from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_extension_suite
from dbtest.mixins import touch_input_files, remove_input_files

class FilesEventTestCase(EventTestCase):
  moduleid = 'files'
  eventid  = 'files'
  _conf = """<files>
    <path>/tmp/outfile</path>
    <path dest='/infiles'>infile</path>
    <path dest='/infiles'>infile2</path>
  </files>"""

  def setUp(self):
    EventTestCase.setUp(self)
    if self.event:
      touch_input_files(self.event._config.file.abspath().dirname)

  def tearDown(self):
    if self.event:
      remove_input_files(self.event._config.file.abspath().dirname)
    EventTestCase.tearDown(self)

def make_suite(basedistro):
  suite = ModuleTestSuite('files')

  suite.addTest(make_extension_suite(FilesEventTestCase, basedistro))

  return suite
