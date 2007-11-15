import unittest

from dims import pps

from test             import EventTestRunner
from test.events      import make_core_suite
from test.events.rpms import RpmBuildMixinTestCase, RpmCvarsTestCase

eventid = 'theme-rpm'

class Test_ThemeRpmBuild(RpmBuildMixinTestCase):
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

class Test_ThemeRpmCvars1(RpmCvarsTestCase):
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
    self.failUnless((self.event.rpmname, 'conditional', 'gdm', self.event.obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ThemeRpmCvars2(RpmCvarsTestCase):
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
    self.failUnless((self.event.rpmname, 'conditional', 'gdm', self.event.obsoletes, None) in
                    self.event.cvars['custom-rpms-info'])
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(Test_ThemeRpmBuild(conf))
  suite.addTest(Test_ThemeRpmCvars1(conf))
  suite.addTest(Test_ThemeRpmCvars2(conf))
  return suite

def main(suite=None):
  import dims.pps
  config = dims.pps.Path(__file__).dirname/'%s.conf' % eventid
  if suite:
    suite.addTest(make_suite(config))
  else:
    runner = EventTestRunner()
    runner.run(make_suite(config))


if __name__ == '__main__':
  main()
