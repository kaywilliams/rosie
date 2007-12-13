from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_extension_suite
from dbtest.mixins import touch_input_files, remove_input_files

class FilesTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'files', conf)

def make_suite():
  suite = ModuleTestSuite('files')

  suite.addTest(make_extension_suite('files'))

  return suite
