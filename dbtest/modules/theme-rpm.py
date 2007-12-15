from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite, make_extension_suite
from dbtest.rpms import RpmBuildMixinTestCase, RpmCvarsTestCase

class ThemeRpmEventTestCase(EventTestCase):
  moduleid = 'theme-rpm'
  eventid  = 'theme-rpm'
  _conf = """<theme-rpm enabled="true"/>"""

class Test_ThemeRpmBuild(RpmBuildMixinTestCase, ThemeRpmEventTestCase):
  def setUp(self):
    ThemeRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ThemeRpmCvars1(RpmCvarsTestCase, ThemeRpmEventTestCase):
  def setUp(self):
    ThemeRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'conditional', 'gdm',
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ThemeRpmCvars2(RpmCvarsTestCase, ThemeRpmEventTestCase):
  def setUp(self):
    ThemeRpmEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'conditional', 'gdm',
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite():
  suite = ModuleTestSuite('theme-rpm')

  suite.addTest(make_extension_suite(ThemeRpmEventTestCase))
  suite.addTest(Test_ThemeRpmBuild())
  suite.addTest(Test_ThemeRpmCvars1())
  suite.addTest(Test_ThemeRpmCvars2())

  return suite
