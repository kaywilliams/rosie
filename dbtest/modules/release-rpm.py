from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite
from dbtest.rpms import (RpmBuildMixinTestCase, InputFilesMixinTestCase,
                         RpmCvarsTestCase, ExtractMixin, RpmEventTestCase)

class ReleaseRpmEventTestCase(EventTestCase):
  moduleid = 'release-rpm'
  eventid  = 'release-rpm'
  _conf = """<release-rpm enabled="true"/>"""

class Test_ReleaseRpmInputs(InputFilesMixinTestCase, ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ReleaseRpmEventTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmBuild(RpmBuildMixinTestCase, ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars1(RpmCvarsTestCase, ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars2(RpmCvarsTestCase, ReleaseRpmEventTestCase):
  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()
    self.failUnless((self.event.rpm_name, 'mandatory', None,
                     self.event.rpm_obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_RNotesExistence(RpmEventTestCase, ExtractMixin, ReleaseRpmEventTestCase):
  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ReleaseRpmEventTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())
    rnotes = self.img_path.findpaths(glob='RELEASE-NOTES*')
    self.failIf(len(rnotes) == 0)

def make_suite(basedistro):
  suite = ModuleTestSuite('release-rpm')

  suite.addTest(make_core_suite(ReleaseRpmEventTestCase, basedistro))
  suite.addTest(Test_ReleaseRpmInputs(basedistro))
  suite.addTest(Test_ReleaseRpmBuild(basedistro))
  suite.addTest(Test_ReleaseRpmCvars1(basedistro))
  suite.addTest(Test_ReleaseRpmCvars2(basedistro))
  suite.addTest(Test_RNotesExistence(basedistro))

  return suite
