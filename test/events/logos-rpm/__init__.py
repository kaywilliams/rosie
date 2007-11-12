import unittest

from dims import pps

from test import EventTest

from test.events.core import make_suite as core_make_suite
from test.events.rpms import RpmBuildMixinTestCase, LocalFilesMixinTestCase, RpmCvarsTestCase

eventid = 'logos-rpm'

class Test_LogosRpmLocals(LocalFilesMixinTestCase):
  def __init__(self, conf):
    LocalFilesMixinTestCase.__init__(self, eventid, conf)

  def setUp(self):
    LocalFilesMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    LocalFilesMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_locals()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmBuild(RpmBuildMixinTestCase):
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
    self.failUnless((self.event.rpmname, 'mandatory', None, self.event.obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_LogosRpmCvars1(RpmCvarsTestCase):
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

class Test_LogosRpmCvars2(RpmCvarsTestCase):
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

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, conf))
  suite.addTest(Test_LogosRpmLocals(conf))
  suite.addTest(Test_LogosRpmBuild(conf))
  suite.addTest(Test_LogosRpmCvars1(conf))
  suite.addTest(Test_LogosRpmCvars2(conf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)

  #suite = make_suite(dims.pps.Path('%s.conf' % eventid).abspath())
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)

  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)

if __name__ == '__main__':
  main()
