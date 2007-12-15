from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite
from dbtest.rpms import RpmBuildMixinTestCase, RpmCvarsTestCase

class LogosRpmEventTestCase(EventTestCase):
  moduleid = 'logos-rpm'
  eventid  = 'logos-rpm'
  _conf = """<logos-rpm enabled="true"/>"""

class Test_LogosRpmBuild(RpmBuildMixinTestCase, LogosRpmEventTestCase):
  def setUp(self):
    LogosRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmCvars1(RpmCvarsTestCase, LogosRpmEventTestCase):
  def setUp(self):
    LogosRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmCvars2(RpmCvarsTestCase, LogosRpmEventTestCase):
  def setUp(self):
    LogosRpmEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite():
  suite = ModuleTestSuite('logos-rpm')

  suite.addTest(make_core_suite(LogosRpmEventTestCase))
  suite.addTest(Test_LogosRpmBuild())
  suite.addTest(Test_LogosRpmCvars1())
  suite.addTest(Test_LogosRpmCvars2())

  return suite
