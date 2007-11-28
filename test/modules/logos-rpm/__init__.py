import unittest

from dims import pps

from test.core import make_core_suite
from test.rpms import RpmBuildMixinTestCase, LocalFilesMixinTestCase, RpmCvarsTestCase

class Test_LogosRpmLocals(LocalFilesMixinTestCase):
  def __init__(self, conf):
    LocalFilesMixinTestCase.__init__(self, 'logos-rpm', conf)

  def setUp(self):
    LocalFilesMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    LocalFilesMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_locals()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmBuild(RpmBuildMixinTestCase):
  def __init__(self, conf):
    RpmBuildMixinTestCase.__init__(self, 'logos-rpm', conf)

  def setUp(self):
    RpmBuildMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    RpmBuildMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='logos-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmCvars1(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, 'logos-rpm', conf)

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

class Test_LogosRpmCvars2(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, 'logos-rpm', conf)

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
  conf = pps.Path(__file__).dirname/'logos-rpm.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('logos-rpm', conf))
  suite.addTest(Test_LogosRpmLocals(conf))
  suite.addTest(Test_LogosRpmBuild(conf))
  suite.addTest(Test_LogosRpmCvars1(conf))
  suite.addTest(Test_LogosRpmCvars2(conf))
  
  return suite
