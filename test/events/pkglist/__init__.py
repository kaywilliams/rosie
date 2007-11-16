import unittest

from test import EventTestCase, EventTestRunner

from test.events import make_core_suite

eventid = 'pkglist'

class PkglistEventTestCase(EventTestCase):
  def __init__(self, conf, clean):
    EventTestCase.__init__(self, eventid, conf)
    self.clean = clean

  def setUp(self):
    EventTestCase.setUp(self)
    if self.clean:
      self.clean_event_md()

  def tearDown(self):
    EventTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    count1 = len(self.event.cvars['pkglist'])
    self.reset()
    self.tb.dispatch.execute(until=eventid)
    count2 = len(self.event.cvars['pkglist'])
    self.failUnless(count1 == count2)

  def reset(self):
    self.tb.dispatch.prev()
    self.clean_event_md()
    self.event.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'required-packages\']'],
      'input':     [],
      'output':    [],
    }
    self.event.cvars.pop('pkglist')

class Test_PkglistBug84_1(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, True)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.remove(self.event._config.get('/distro/comps'))

class Test_PkglistBug84_2(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, False)

class Test_PkglistBug84_3(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.remove(self.event._config.get('/distro/comps'))

class Test_PkglistBug85_1(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, True)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.get('/distro/repos').remove(
      self.event._config.get('/distro/repos/repo[@id="fedora-updates"]')
    )

class Test_PkglistBug85_2(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, False)

class Test_PkglistBug85_3(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.get('/distro/repos').remove(
      self.event._config.get('/distro/repos/repo[@id="fedora-updates"]')
    )

class Test_PkglistBug86_1(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, True)

class Test_PkglistBug86_2(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.clean_event_md(self.event._getroot().get('release-rpm'))

def make_suite(confdir):
  suite = unittest.TestSuite()
  config1 = confdir / 'bug84.conf'
  config2 = confdir / 'bug85.conf'
  config3 = confdir / 'bug86.conf'

  suite.addTest(make_core_suite(eventid, config1))

  # test bug 84
  suite.addTest(Test_PkglistBug84_1(config1))
  suite.addTest(Test_PkglistBug84_2(config1))
  suite.addTest(Test_PkglistBug84_3(config1))

  # test bug 85
  suite.addTest(Test_PkglistBug85_1(config2))
  suite.addTest(Test_PkglistBug85_2(config2))
  suite.addTest(Test_PkglistBug85_3(config2))

  # test bug 86
  suite.addTest(Test_PkglistBug86_1(config3))
  suite.addTest(Test_PkglistBug86_2(config3))

  return suite

def main(suite=None):
  import dims.pps
  confdir = dims.pps.Path(__file__).dirname
  if suite:
    suite.addTest(make_suite(confdir))
  else:
    runner = EventTestRunner()
    runner.run(make_suite(confdir))

if __name__ == '__main__':
  main()
