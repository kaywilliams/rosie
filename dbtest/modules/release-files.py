import time

from dims import pps
from dims import xmllib

from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.config import make_default_config
from dbtest.core   import make_core_suite

files = ['input1', 'input2', 'input3']
starttime = time.time()

class ReleaseFilesEventTestCase(EventTestCase):
  _conf = """<release-rpm enabled="true"/>"""
  def __init__(self, conf=None, enabled='True'):
    EventTestCase.__init__(self, 'release-files', conf)
    self.enabled = enabled

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    self.conf.get('release-rpm').attrib['enabled'] = self.enabled

    # touch input files
    for file in files:
      ifilename = self.event._config.file.abspath().dirname/file
      ifilename.touch()
      ifilename.utime((starttime, starttime)) # make sure start times match

  def runTest(self):
    self.tb.dispatch.execute(until='publish')

  def tearDown(self):
    for file in files:
      ifilename = self.event._config.file.abspath().dirname/file
      ifilename.remove()

class Test_ReleaseFiles(ReleaseFilesEventTestCase):
  _conf = [ ReleaseFilesEventTestCase._conf,
  """<release-files enabled="true"/>"""
  ]

class Test_ReleaseFilesWithDefaultSet(ReleaseFilesEventTestCase):
  _conf = [ ReleaseFilesEventTestCase._conf,
  """<release-files>
    <include-in-tree use-default-set="true"/>
  </release-files>"""
  ]

class Test_ReleaseFilesWithDefaultSet(ReleaseFilesEventTestCase):
  _conf = [ ReleaseFilesEventTestCase._conf,
  """<release-files>
    <include-in-tree use-default-set="false"/>
  </release-files>"""
  ]

class Test_ReleaseFilesWithInputFiles(ReleaseFilesEventTestCase):
  _conf = [ ReleaseFilesEventTestCase._conf,
  """<release-files>
    <path>input1</path>
    <path dest="dir1/dir2">input2</path>
    <path dest="dir3">input3</path>
  </release-files>"""
  ]

  def runTest(self):
    ReleaseFilesEventTestCase.runTest(self)
    for file in [ self.event.SOFTWARE_STORE / 'input1',
                  self.event.SOFTWARE_STORE / 'dir1/dir2/input2',
                  self.event.SOFTWARE_STORE / 'dir3/input3']:
      self.failUnlessExists(file)

class Test_ReleaseFilesWithPackageElement(ReleaseFilesEventTestCase):
  _conf = [ ReleaseFilesEventTestCase._conf,
  """<release-files enabled="true">
    <package></package>
  </release-files>"""
  ]

  def __init__(self, conf):
    ReleaseFilesEventTestCase.__init__(self, conf, 'True')

  def setUp(self):
    ReleaseFilesEventTestCase.setUp(self)
    self.conf.get('release-files/package').text = '%s-release' % self.event.product

def make_suite():
  suite = ModuleTestSuite('release-files')

  suite.addTest(make_core_suite('release-files'))

  for distro in [ 'fedora-6',
                  'fedora-7',
                  'fedora-8',
                  'centos-5',
                  'redhat-5', ]:

    # default run
    suite.addTest(Test_ReleaseFiles(make_default_config('release-files', distro), 'True'))
    suite.addTest(Test_ReleaseFiles(make_default_config('release-files', distro), 'False'))

    # execution with modification of 'use-default-set' attribute
    suite.addTest(Test_ReleaseFilesWithDefaultSet(make_default_config('release-files', distro), 'True'))
    suite.addTest(Test_ReleaseFilesWithDefaultSet(make_default_config('release-files', distro), 'False'))

    # execution with <path/> element
    suite.addTest(Test_ReleaseFilesWithInputFiles(make_default_config('release-files', distro), 'True'))
    suite.addTest(Test_ReleaseFilesWithInputFiles(make_default_config('release-files', distro), 'False'))

    # execution with <package/> element
    suite.addTest(Test_ReleaseFilesWithPackageElement(make_default_config('release-files', distro)))

  return suite
