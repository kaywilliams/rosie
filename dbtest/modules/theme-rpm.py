from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite, make_extension_suite
from dbtest.rpms import RpmBuildMixinTestCase, RpmCvarsTestCase

class ThemeRpmTestCase(EventTestCase):
  _conf = """<theme-rpm enabled="true"/>"""
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'theme-rpm', conf)

class Test_ThemeRpmBuild(RpmBuildMixinTestCase, ThemeRpmTestCase):
  def setUp(self):
    RpmBuildMixinTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    RpmBuildMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ThemeRpmCvars1(RpmCvarsTestCase, ThemeRpmTestCase):
  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'conditional', 'gdm',
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ThemeRpmCvars2(RpmCvarsTestCase, ThemeRpmTestCase):
  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.event.status = True

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='theme-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'conditional', 'gdm',
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite():
  suite = ModuleTestSuite('theme-rpm')

  suite.addTest(make_extension_suite('theme-rpm'))
  suite.addTest(Test_ThemeRpmBuild())
  suite.addTest(Test_ThemeRpmCvars1())
  suite.addTest(Test_ThemeRpmCvars2())

  return suite
