from dbtest      import EventTestCase, ModuleTestSuite, config
from dbtest.core import make_core_suite

class Test_GpgKeysNotProvided(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'gpgcheck', conf)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)

def make_suite():
  suite = ModuleTestSuite('gpgcheck')

  suite.addTest(make_core_suite('gpgcheck', _make_conf(keys=True)))
  suite.addTest(Test_GpgKeysNotProvided(_make_conf(keys=False)))

  return suite

def _make_conf(basedistro='fedora-8', keys=True):
  distro = config._make_distro()
  distro.append(config.make_main('gpgcheck'))
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

  distro.append(config.make_repos(basedistro, [repo]))

  return distro
