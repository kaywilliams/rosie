from dims import pps

from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite, make_extension_suite
from dbtest.rpms import ( RpmBuildMixinTestCase, InputFilesMixinTestCase,
                          RpmCvarsTestCase )

class ConfigRpmTestCase(EventTestCase):
  _conf = """<config-rpm enabled="true">
    <requires>yum</requires>
    <requires>createrepo</requires>
  </config-rpm>"""
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'config-rpm', conf)

class Test_ConfigRpmInputs(InputFilesMixinTestCase, ConfigRpmTestCase):
  def setUp(self):
    InputFilesMixinTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    InputFilesMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmBuild(RpmBuildMixinTestCase, ConfigRpmTestCase):
  def setUp(self):
    RpmBuildMixinTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    RpmBuildMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars1(RpmCvarsTestCase, ConfigRpmTestCase):
  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars2(RpmCvarsTestCase, ConfigRpmTestCase):
  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.event.status = True

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite():
  suite = ModuleTestSuite('config-rpm')

  suite.addTest(make_extension_suite('config-rpm'))
  suite.addTest(Test_ConfigRpmInputs())
  suite.addTest(Test_ConfigRpmBuild())
  suite.addTest(Test_ConfigRpmCvars1())
  suite.addTest(Test_ConfigRpmCvars2())

  return suite
