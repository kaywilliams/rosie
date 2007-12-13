from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite
from dbtest.rpms import RpmBuildMixinTestCase, RpmCvarsTestCase

class LogosRpmTestCase(EventTestCase):
  _conf = """<logos-rpm enabled="true"/>"""
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'logos-rpm', conf)

class Test_LogosRpmBuild(RpmBuildMixinTestCase, LogosRpmTestCase):
  def setUp(self):
    RpmBuildMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    RpmBuildMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmCvars1(RpmCvarsTestCase, LogosRpmTestCase):
  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmCvars2(RpmCvarsTestCase, LogosRpmTestCase):
  def setUp(self):
    RpmCvarsTestCase.setUp(self)

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite():
  suite = ModuleTestSuite('logos-rpm')

  suite.addTest(make_core_suite('logos-rpm'))
  suite.addTest(Test_LogosRpmLocals())
  suite.addTest(Test_LogosRpmBuild())
  suite.addTest(Test_LogosRpmCvars1())
  suite.addTest(Test_LogosRpmCvars2())

  return suite
