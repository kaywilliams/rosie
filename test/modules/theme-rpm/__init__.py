import unittest

from dims import pps

from test.core import make_core_suite, make_extension_suite
from test.rpms import RpmBuildMixinTestCase, RpmCvarsTestCase

class Test_ThemeRpmBuild(RpmBuildMixinTestCase):
  def __init__(self, conf):
    RpmBuildMixinTestCase.__init__(self, 'theme-rpm', conf)

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

class Test_ThemeRpmCvars1(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, 'theme-rpm', conf)

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

class Test_ThemeRpmCvars2(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, 'theme-rpm', conf)

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
  conf = pps.Path(__file__).dirname/'theme-rpm.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('theme-rpm', conf))
  suite.addTest(make_extension_suite('theme-rpm', conf))
  suite.addTest(Test_ThemeRpmBuild(conf))
  suite.addTest(Test_ThemeRpmCvars1(conf))
  suite.addTest(Test_ThemeRpmCvars2(conf))
  
  return suite
