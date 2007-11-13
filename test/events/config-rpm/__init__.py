import unittest

from dims import pps

from test import EventTest

from test.events.core import make_suite as core_make_suite
from test.events.rpms import RpmBuildMixinTestCase, InputFilesMixinTestCase, RpmCvarsTestCase

eventid = 'config-rpm'

class Test_ConfigRpmInputs(InputFilesMixinTestCase):
  def __init__(self, conf):
    InputFilesMixinTestCase.__init__(self, eventid, conf)

  def setUp(self):
    InputFilesMixinTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    InputFilesMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmBuild(RpmBuildMixinTestCase):
  def __init__(self, conf):
    RpmBuildMixinTestCase.__init__(self, eventid, conf)

  def setUp(self):
    RpmBuildMixinTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    RpmBuildMixinTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars1(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, eventid, conf)

  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    RpmCvarsTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    self.check_cvars()
    self.failUnless((self.event.rpmname, 'mandatory', None, self.event.obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars2(RpmCvarsTestCase):
  def __init__(self, conf):
    RpmCvarsTestCase.__init__(self, eventid, conf)

  def setUp(self):
    RpmCvarsTestCase.setUp(self)
    self.event.status = True

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
  suite.addTest(Test_ConfigRpmInputs(conf))
  suite.addTest(Test_ConfigRpmBuild(conf))
  suite.addTest(Test_ConfigRpmCvars1(conf))
  suite.addTest(Test_ConfigRpmCvars2(conf))
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
