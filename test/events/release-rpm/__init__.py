import unittest

from dims import pps

from test      import EventTestRunner
from test.core import make_core_suite
from test.rpms import (RpmBuildMixinTestCase, InputFilesMixinTestCase,
                       RpmCvarsTestCase, ExtractMixin, RpmEventTestCase)

eventid = 'release-rpm'

class Test_ReleaseRpmInputs(InputFilesMixinTestCase):
  def __init__(self, conf):
    InputFilesMixinTestCase.__init__(self, eventid, conf)

  def setUp(self):
    InputFilesMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    InputFilesMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmBuild(RpmBuildMixinTestCase):
  def __init__(self, conf):
    RpmBuildMixinTestCase.__init__(self, eventid, conf)

  def setUp(self):
    RpmBuildMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    RpmBuildMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars1(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, eventid, conf)

  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_cvars()
    self.failUnless((self.event.rpmname, 'mandatory', None, self.event.obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars2(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, eventid, conf)

  def setUp(self):
    RpmCvarsTestCase.setUp(self)

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_cvars()
    self.failUnless((self.event.rpmname, 'mandatory', None, self.event.obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_RNotesExistence(RpmEventTestCase, ExtractMixin):
  def __init__(self, conf):
    RpmEventTestCase.__init__(self, eventid, conf)
    ExtractMixin.__init__(self)

  def setUp(self):
    RpmEventTestCase.setUp(self)

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    RpmEventTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.failUnless(self.event.verifier.unittest().wasSuccessful())
    rnotes = self.img_path.findpaths(glob='RELEASE-NOTES*')
    self.failIf(len(rnotes) == 0)

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(Test_ReleaseRpmInputs(conf))
  suite.addTest(Test_ReleaseRpmBuild(conf))
  suite.addTest(Test_ReleaseRpmCvars1(conf))
  suite.addTest(Test_ReleaseRpmCvars2(conf))
  suite.addTest(Test_RNotesExistence(conf))
  return suite

def main(suite=None):
  import dims.pps
  config = dims.pps.Path(__file__).dirname/'%s.conf' % eventid
  if suite:
    suite.addTest(make_suite(config))
  else:
    EventTestRunner().run(make_suite(config))


if __name__ == '__main__':
  main()
