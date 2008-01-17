from rendition import pps

from spintest      import EventTestCase, ModuleTestSuite
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
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ConfigRpmEventTestCase.tearDown(self)

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
