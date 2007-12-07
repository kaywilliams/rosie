from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite
from dbtest.rpms import (RpmBuildMixinTestCase, InputFilesMixinTestCase,
                           RpmCvarsTestCase, ExtractMixin, RpmEventTestCase)

class ReleaseRpmTestCase(EventTestCase):
  _conf = """<release-rpm enabled="true"/>"""
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'release-rpm', conf)

class Test_ReleaseRpmInputs(InputFilesMixinTestCase, ReleaseRpmTestCase):
  def setUp(self):
    InputFilesMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    InputFilesMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmBuild(RpmBuildMixinTestCase, ReleaseRpmTestCase):
  def setUp(self):
    RpmBuildMixinTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars1(RpmCvarsTestCase, ReleaseRpmTestCase):
  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars2(RpmCvarsTestCase, ReleaseRpmTestCase):
  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_RNotesExistence(RpmEventTestCase, ExtractMixin, ReleaseRpmTestCase):
  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    RpmEventTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())
    rnotes = self.img_path.findpaths(glob='RELEASE-NOTES*')
    self.failIf(len(rnotes) == 0)

def make_suite():
  suite = ModuleTestSuite('release-rpm')

  suite.addTest(make_core_suite('release-rpm'))
  suite.addTest(Test_ReleaseRpmInputs())
  suite.addTest(Test_ReleaseRpmBuild())
  suite.addTest(Test_ReleaseRpmCvars1())
  suite.addTest(Test_ReleaseRpmCvars2())
  suite.addTest(Test_RNotesExistence())

  return suite
