import unittest

from dims import pps

from test.core import make_core_suite, make_extension_suite
from test.rpms import RpmBuildMixinTestCase, InputFilesMixinTestCase, RpmCvarsTestCase

class Test_ConfigRpmInputs(InputFilesMixinTestCase):
  def __init__(self, conf):
    InputFilesMixinTestCase.__init__(self, 'config-rpm', conf)

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

class Test_ConfigRpmBuild(RpmBuildMixinTestCase):
  def __init__(self, conf):
    RpmBuildMixinTestCase.__init__(self, 'config-rpm', conf)

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

class Test_ConfigRpmCvars1(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, 'config-rpm', conf)

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

class Test_ConfigRpmCvars2(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, 'config-rpm', conf)

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
  conf = pps.Path(__file__).dirname/'config-rpm.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('config-rpm', conf))
  suite.addTest(make_extension_suite('config-rpm', conf))
  suite.addTest(Test_ConfigRpmInputs(conf))
  suite.addTest(Test_ConfigRpmBuild(conf))
  suite.addTest(Test_ConfigRpmCvars1(conf))
  suite.addTest(Test_ConfigRpmCvars2(conf))
  
  return suite
