from spintest      import EventTestCase, ModuleTestSuite, config
from spintest.core import make_core_suite

def _make_conf(basedistro='fedora-6', keys=True):
  if keys:
    repo = config._make_repo('%s-base' % basedistro, enabled='1', gpgcheck='1')
  else:
    repo = config._make_repo('%s-base' % basedistro, enabled='1', gpgcheck='1', gpgkey='')

  # hack, shouldn't have to convert back to string
  return str(config.make_repos(basedistro, [repo]))

class GpgcheckEventTestCase(EventTestCase):
  moduleid = 'gpgcheck'
  eventid  = 'gpgcheck'
  def __init__(self, basedistro, arch, conf=None):
    self._conf = _make_conf(basedistro)
    EventTestCase.__init__(self, basedistro, arch, conf)

class Test_GpgKeysNotProvided(GpgcheckEventTestCase):
  "raises RuntimeError when no keys are provided"
  def __init__(self, basedistro, arch, conf=None):
    self._conf = _make_conf(basedistro, keys=False)
    EventTestCase.__init__(self, basedistro, arch, conf)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('gpgcheck')

  suite.addTest(make_core_suite(GpgcheckEventTestCase, basedistro, arch))
  suite.addTest(Test_GpgKeysNotProvided(basedistro, arch))

  return suite
