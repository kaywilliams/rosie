import unittest

from dims import pps
from dims import xmllib

from dbtest      import EventTestCase
from dbtest.core import make_core_suite

P = pps.Path

class PkglistEventTestCase(EventTestCase):

  PKGLIST_COUNT = {}

  def __init__(self, conf, caseid, clean=False):
    EventTestCase.__init__(self, 'pkglist', conf)
    self.caseid = caseid
    self.clean = clean

  def setUp(self):
    EventTestCase.setUp(self)
    if self.clean:
      self.clean_event_md()

  def tearDown(self):
    EventTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.PKGLIST_COUNT[self.caseid] = len(self.event.cvars['pkglist'])

  def getPkglistCount(self, caseid):
    return self.PKGLIST_COUNT.get(caseid)

class Test_PkglistBug84_1(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug84_1', True)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.remove(self.event._config.get('/distro/comps'))

class Test_PkglistBug84_2(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug84_2', False)

class Test_PkglistBug84_3(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug84_3', False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.remove(self.event._config.get('/distro/comps'))

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug84_1')
    count2 = self.getPkglistCount('bug84_3')
    self.failUnless(count1 == count2,
      "incremental depsolve: %d, forced depsolve: %d" % (count1, count2))

class Test_PkglistBug85_1(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug85_1', True)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.get('/distro/repos').remove(
      self.event._config.get('/distro/repos/repo[@id="fedora-updates"]')
    )

class Test_PkglistBug85_2(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug85_2', False)

class Test_PkglistBug85_3(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug85_3', False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.get('/distro/repos').remove(
      self.event._config.get('/distro/repos/repo[@id="fedora-updates"]')
    )

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug85_1')
    count2 = self.getPkglistCount('bug85_3')
    self.failUnless(count1 == count2, "bug85_1: %d packages; bug85_3: %d packages" % \
                    (count1, count2))

class Test_PkglistBug86_1(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug86_1', True)

class Test_PkglistBug86_2(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug86_2', False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.clean_event_md(self.event._getroot().get('release-rpm'))

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug86_1')
    count2 = self.getPkglistCount('bug86_2')
    self.failUnless(count1 == count2)

class Test_PkglistBug108_1(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug108_1', True)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.event._config.get('/distro/repos').remove(
      self.event._config.get('/distro/repos/repo[@id="updates"]')
    )

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    found_gaim = False
    found_pidgin = False
    found_libpurple = False
    for package in self.event.cvars['pkglist']:
      if package.startswith('gaim'):
        found_gaim = True
      if package.startswith('pidgin'):
        found_pidgin = True
      if package.startswith('libpurple'):
        found_libpurple = True

    self.failUnless(found_gaim)
    self.failIf(found_pidgin or found_libpurple)

class Test_PkglistBug108_2(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'bug108_2', False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    found_gaim = False
    found_pidgin = False
    found_libpurple = False
    for package in self.event.cvars['pkglist']:
      if package.startswith('gaim'):
        found_gaim = True
      if package.startswith('pidgin'):
        found_pidgin = True
      if package.startswith('libpurple'):
        found_libpurple = True

    self.failUnless(found_pidgin or found_libpurple)
    self.failIf(found_gaim)

class Test_Supplied(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'pkglist', conf)
    self.working_dir = P(conf.dirname)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    pkglist_in  = (self.working_dir / self.event.config.get('text()')).read_lines()
    pkglist_out = self.event.cvars['pkglist']
    self.failUnlessEqual(sorted(pkglist_in), sorted(pkglist_out))

class Test_PackageAdded(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'pkgadded', True)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    xmllib.tree.Element('repofile', self.event._config.get('repos'),
                        text='pkglist-test-repos1.repo')
    comps = xmllib.tree.Element('comps', self.event._config.getroot())
    core = xmllib.tree.Element('core', comps)
    pkg1 = xmllib.tree.Element('package', core, 'pkglist-test-package1')

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package1-1.0-1' in self.event.cvars['pkglist'])

class Test_ObsoletedPackage(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'pkgobsoleted', False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    xmllib.tree.Element('repofile', self.event._config.get('repos'),
                        text='pkglist-test-repos1.repo')
    xmllib.tree.Element('repofile', self.event._config.get('repos'),
                        text='pkglist-test-repos2.repo')
    comps = xmllib.tree.Element('comps', self.event._config.getroot())
    core = xmllib.tree.Element('core', comps)
    pkg1 = xmllib.tree.Element('package', core, 'pkglist-test-package2')

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package2-1.0-1' in self.event.cvars['pkglist'])
    self.failIf('pkglist-test-package1-1.0-1' in self.event.cvars['pkglist'])

class Test_RemovedPackage(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'pkgremoved', False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failIf('pkglist-test-package2-1.0-1' in self.event.cvars['pkglist'])

class Test_ExclusivePackage_1(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'exclusive_1', False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    xmllib.tree.Element('repofile', self.event._config.get('repos'),
                        text='pkglist-test-repos3.repo')
    comps = xmllib.tree.Element('comps', self.event._config.getroot())
    core = xmllib.tree.Element('core', comps)
    pkg1 = xmllib.tree.Element('package', core, 'pkglist-test-package3')

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package3-1.0-1' in self.event.cvars['pkglist'])
    self.failUnless('pkglist-test-package4-1.0-1' in self.event.cvars['pkglist'])

class Test_ExclusivePackage_2(PkglistEventTestCase):
  def __init__(self, conf):
    PkglistEventTestCase.__init__(self, conf, 'exclusive_2', False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failIf('pkglist-test-package3-1.0-1' in self.event.cvars['pkglist'])
    self.failIf('pkglist-test-package4-1.0-1' in self.event.cvars['pkglist'])


def make_suite():
  confdir = pps.Path(__file__).dirname
  suite = unittest.TestSuite()

  # core tests
  suite.addTest(make_core_suite('pkglist', confdir / 'pkglist.conf'))

  # bug 84
  config = confdir / 'bug84.conf'
  bug84 = unittest.TestSuite()
  bug84.addTest(Test_PkglistBug84_1(config))
  bug84.addTest(Test_PkglistBug84_2(config))
  bug84.addTest(Test_PkglistBug84_3(config))
  suite.addTest(bug84)

  # bug 85
  config = confdir / 'bug85.conf'
  bug85 = unittest.TestSuite()
  bug85.addTest(Test_PkglistBug85_1(config))
  bug85.addTest(Test_PkglistBug85_2(config))
  bug85.addTest(Test_PkglistBug85_3(config))
  suite.addTest(bug85)

  # bug 86
  config = confdir / 'bug86.conf'
  bug86 = unittest.TestSuite()
  bug86.addTest(Test_PkglistBug86_1(config))
  bug86.addTest(Test_PkglistBug86_2(config))
  suite.addTest(bug86)

  # bug 108
  config = confdir / 'bug108.conf'
  bug108 = unittest.TestSuite()
  bug108.addTest(Test_PkglistBug108_1(config))
  bug108.addTest(Test_PkglistBug108_2(config))
  suite.addTest(bug108)

  # pkglist supplied
  config = confdir / 'supplied.conf'
  suite.addTest(Test_Supplied(config))

  config = confdir / 'pkglist.conf'
  # package added, obsoleted, and removed
  suite.addTest(Test_PackageAdded(config))
  suite.addTest(Test_ObsoletedPackage(config))
  suite.addTest(Test_RemovedPackage(config))

  # add package that requires a package nothing else requires,
  # then remove it.
  suite.addTest(Test_ExclusivePackage_1(config))
  suite.addTest(Test_ExclusivePackage_2(config))

  return suite
