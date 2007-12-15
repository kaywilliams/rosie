from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import touch_input_files, remove_input_files


class ReleaseFilesEventTestCase(EventTestCase):
  moduleid = 'release-files'
  eventid  = 'release-files'
  _conf = """<release-rpm enabled="true"/>"""
  def __init__(self, conf=None, enabled='True'):
    EventTestCase.__init__(self, conf)
    self.enabled = enabled

class _ReleaseFilesEventTestCase(ReleaseFilesEventTestCase):
  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    self.conf.get('release-rpm').attrib['enabled'] = self.enabled

    # touch input files
    touch_input_files(self.event._config.file.abspath().dirname)

  def runTest(self):
    self.tb.dispatch.execute(until='publish')

  def tearDown(self):
    remove_input_files(self.event._config.file.abspath().dirname)
    ReleaseFilesEventTestCase.tearDown(self)


class Test_ReleaseFiles(_ReleaseFilesEventTestCase):
  _conf = [ _ReleaseFilesEventTestCase._conf,
  """<release-files enabled="true"/>"""
  ]

class Test_ReleaseFilesWithDefaultSet(_ReleaseFilesEventTestCase):
  _conf = [ _ReleaseFilesEventTestCase._conf,
  """<release-files>
    <include-in-tree use-default-set="true"/>
  </release-files>"""
  ]

class Test_ReleaseFilesWithDefaultSet(_ReleaseFilesEventTestCase):
  _conf = [ _ReleaseFilesEventTestCase._conf,
  """<release-files>
    <include-in-tree use-default-set="false"/>
  </release-files>"""
  ]

class Test_ReleaseFilesWithInputFiles(_ReleaseFilesEventTestCase):
  _conf = [ _ReleaseFilesEventTestCase._conf,
  """<release-files>
    <path>/tmp/outfile</path>
    <path dest="/infiles">infile</path>
    <path dest="/infiles">infile2</path>
  </release-files>"""
  ]

class Test_ReleaseFilesWithPackageElement(_ReleaseFilesEventTestCase):
  _conf = [ _ReleaseFilesEventTestCase._conf,
  """<release-files enabled="true">
    <package></package>
  </release-files>"""
  ]

  def __init__(self, conf=None):
    _ReleaseFilesEventTestCase.__init__(self, conf, 'True')

  def setUp(self):
    _ReleaseFilesEventTestCase.setUp(self)
    self.conf.get('release-files/package').text = '%s-release' % self.event.product

def make_suite():
  suite = ModuleTestSuite('release-files')

  suite.addTest(make_core_suite(ReleaseFilesEventTestCase))

  # default run
  suite.addTest(Test_ReleaseFiles(enabled='True'))
  suite.addTest(Test_ReleaseFiles(enabled='False'))

  # execution with modification of 'use-default-set' attribute
  suite.addTest(Test_ReleaseFilesWithDefaultSet(enabled='True'))
  suite.addTest(Test_ReleaseFilesWithDefaultSet(enabled='False'))

  # execution with <path/> element
  suite.addTest(Test_ReleaseFilesWithInputFiles(enabled='True'))
  suite.addTest(Test_ReleaseFilesWithInputFiles(enabled='False'))

  # execution with <package/> element
  suite.addTest(Test_ReleaseFilesWithPackageElement())

  return suite
