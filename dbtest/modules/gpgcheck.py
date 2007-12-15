from dbtest      import EventTestCase, ModuleTestSuite, config
from dbtest.core import make_core_suite

def _make_conf(basedistro='fedora-6', keys=True):
  if keys:
    keyroot = config.REPOS['%s-base' % basedistro]['baseurl']
    repo = config._make_repo('%s-base' % basedistro, enabled='1', gpgcheck='1',
             gpgkey='\n'.join(['%s/RPM-GPG-KEY' % keyroot,
                               '%s/RPM-GPG-KEY-beta' % keyroot,
                               '%s/RPM-GPG-KEY-fedora' % keyroot,
                               '%s/RPM-GPG-KEY-fedora-rawhide' % keyroot,
                               '%s/RPM-GPG-KEY-fedora-test' % keyroot,
                               '%s/RPM-GPG-KEY-rawhide' % keyroot]))
  else:
    repo = config._make_repo('%s-base' % basedistro, enabled='1', gpgcheck='1')

  # hack, shouldn't have to convert back to string
  return str(config.make_repos(basedistro, [repo]))

class GpgcheckEventTestCase(EventTestCase):
  moduleid = 'gpgcheck'
  eventid  = 'gpgcheck'
  _conf = _make_conf()

class Test_GpgKeysNotProvided(GpgcheckEventTestCase):
  "raises RuntimeError when no keys are provided"
  _conf = _make_conf(keys=False)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)

def make_suite():
  suite = ModuleTestSuite('gpgcheck')

  suite.addTest(make_core_suite(GpgcheckEventTestCase))
  suite.addTest(Test_GpgKeysNotProvided())

  return suite
