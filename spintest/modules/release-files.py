from spintest        import EventTestCase, ModuleTestSuite
from spintest.config import add_config_section
from spintest.core   import make_core_suite
from spintest.mixins import touch_input_files, remove_input_files


class ReleaseFilesEventTestCase(EventTestCase):
  moduleid = 'release-files'
  eventid  = 'release-files'
  _conf = """<release-files/>"""

  def __init__(self, basedistro, arch, conf=None, enabled='True'):
    EventTestCase.__init__(self, basedistro, arch, conf)
    self.enabled = enabled

class _ReleaseFilesEventTestCase(ReleaseFilesEventTestCase):
  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    add_config_section(self.conf, "<release-rpm enabled='%s'/>" % self.enabled)

    # touch input files
    touch_input_files(self.event._config.file.abspath().dirname)

  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)

  def tearDown(self):
    remove_input_files(self.event._config.file.abspath().dirname)
    ReleaseFilesEventTestCase.tearDown(self)


class Test_ReleaseFiles(_ReleaseFilesEventTestCase):
  _conf = """<release-files enabled="true"/>"""

class Test_ReleaseFilesWithDefaultSet(_ReleaseFilesEventTestCase):
  _conf = """<release-files use-default-set="true"/>"""

class Test_ReleaseFilesWithDefaultSet(_ReleaseFilesEventTestCase):
  _conf = """<release-files use-default-set="false"/>"""

class Test_ReleaseFilesWithInputFiles(_ReleaseFilesEventTestCase):
  _conf = """<release-files>
    <path>/tmp/outfile</path>
    <path dest="/infiles">infile</path>
    <path dest="/infiles">infile2</path>
  </release-files>"""

class Test_ReleaseFilesWithPackageElement(_ReleaseFilesEventTestCase):
  _conf = """<release-files>
    <package></package>
  </release-files>"""
  # this test doesn't actually do anything because package is empty...

  def __init__(self, basedistro, arch, conf=None):
    _ReleaseFilesEventTestCase.__init__(self, basedistro, arch, conf, 'True')

  def setUp(self):
    _ReleaseFilesEventTestCase.setUp(self)
    self.conf.get('release-files/package').text = '%s-release' % self.event.product

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('release-files')

  suite.addTest(make_core_suite(ReleaseFilesEventTestCase, basedistro, arch))

  # default run
  suite.addTest(Test_ReleaseFiles(basedistro, arch, enabled='True'))
  suite.addTest(Test_ReleaseFiles(basedistro, arch, enabled='False'))

  # execution with modification of 'use-default-set' attribute
  suite.addTest(Test_ReleaseFilesWithDefaultSet(basedistro, arch, enabled='True'))
  suite.addTest(Test_ReleaseFilesWithDefaultSet(basedistro, arch, enabled='False'))

  # execution with <path/> element
  suite.addTest(Test_ReleaseFilesWithInputFiles(basedistro, arch, enabled='True'))
  suite.addTest(Test_ReleaseFilesWithInputFiles(basedistro, arch, enabled='False'))

  # execution with <package/> element
  suite.addTest(Test_ReleaseFilesWithPackageElement(basedistro, arch))

  return suite
