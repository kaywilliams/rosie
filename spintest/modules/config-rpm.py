from rendition import pps

from spintest      import BUILD_ROOT, EventTestCase, ModuleTestSuite, config
from spintest.core import make_core_suite, make_extension_suite
from spintest.rpms import ( RpmBuildMixinTestCase, InputFilesMixinTestCase,
                            RpmCvarsTestCase )

class ConfigRpmEventTestCase(EventTestCase):
  moduleid = 'config-rpm'
  eventid  = 'config-rpm'
  _conf = """<config-rpm enabled="true">
    <requires>yum</requires>
    <requires>createrepo</requires>
  </config-rpm>"""

class Test_ConfigRpmInputs(InputFilesMixinTestCase, ConfigRpmEventTestCase):
  def __init__(self, basedistro, arch, conf=None):
    ConfigRpmEventTestCase.__init__(self, basedistro, arch, conf=conf)

    self.working_dir = BUILD_ROOT
    self.file1 = pps.Path('%s/file1' % self.working_dir)
    self.file2 = pps.Path('%s/file2' % self.working_dir)
    self.file3 = pps.Path('%s/file3' % self.working_dir)
    self.script1 = pps.Path('%s/script1' % self.working_dir)
    self.script2 = pps.Path('%s/script2' % self.working_dir)

    config.add_config_section(
      self.conf,
      """
      <config-rpm enabled="true">
        <file>%s/file1</file>
        <file dest="/etc/testdir">%s/file2</file>
        <file filename="filename">%s/file3</file>
        <script>%s/script1</script>
        <script dest="/usr/bin">%s/script2</script>
      </config-rpm>
      """ % ((self.working_dir,)*5)
    )

  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.file1.touch()
    self.file2.touch()
    self.file3.touch()
    self.script1.touch()
    self.script2.touch()
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ConfigRpmEventTestCase.tearDown(self)
    self.file1.rm(force=True)
    self.file2.rm(force=True)
    self.file3.rm(force=True)
    self.script1.rm(force=True)
    self.script2.rm(force=True)

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmBuild(RpmBuildMixinTestCase, ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars1(RpmCvarsTestCase, ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars2(RpmCvarsTestCase, ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('config-rpm')

  suite.addTest(make_extension_suite(ConfigRpmEventTestCase, basedistro, arch))
  suite.addTest(Test_ConfigRpmInputs(basedistro, arch))
  suite.addTest(Test_ConfigRpmBuild(basedistro, arch))
  suite.addTest(Test_ConfigRpmCvars1(basedistro, arch))
  suite.addTest(Test_ConfigRpmCvars2(basedistro, arch))

  return suite
