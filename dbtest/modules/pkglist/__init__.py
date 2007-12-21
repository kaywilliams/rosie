from StringIO import StringIO

import unittest

from dims import pps
from dims import xmllib

from dbtest      import EventTestCase, ModuleTestSuite, config
from dbtest.core import make_core_suite

P = pps.Path

class DummyPkglistEventTestCase(EventTestCase):
  moduleid = 'pkglist'
  eventid  = 'pkglist'

class PkglistEventTestCase(EventTestCase):
  moduleid = 'pkglist'
  eventid  = 'pkglist'

  PKGLIST_COUNT = {}

  def __init__(self, caseid, basedistro, clean=False):
    EventTestCase.__init__(self, basedistro=basedistro)
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
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug84_1', basedistro, True)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro)]
      )
    )

class Test_PkglistBug84_2(PkglistEventTestCase):
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug84_2', basedistro, False)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro)]
      )
    )
    config.add_config_section(
      self.conf,
      """
      <comps>
        <core>
          <group>base</group>
        </core>
      </comps>
      """
    )

class Test_PkglistBug84_3(PkglistEventTestCase):
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug84_3', basedistro, False)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro)]
      )
    )

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug84_1')
    count2 = self.getPkglistCount('bug84_3')
    self.failUnless(count1 == count2,
      "incremental depsolve: %d, forced depsolve: %d" % (count1, count2))

class Test_PkglistBug85_1(PkglistEventTestCase):
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug85_1', basedistro, True)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro)]
      )
    )

class Test_PkglistBug85_2(PkglistEventTestCase):
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug85_2', basedistro, False)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro),
         config._make_repo('%s-updates' % basedistro)]
      )
    )

class Test_PkglistBug85_3(PkglistEventTestCase):
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug85_3', basedistro, False)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro)]
      )
    )

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug85_1')
    count2 = self.getPkglistCount('bug85_3')
    self.failUnless(count1 == count2, "bug85_1: %d packages; bug85_3: %d packages" % \
                    (count1, count2))

class Test_PkglistBug86_1(PkglistEventTestCase):
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug86_1', basedistro, True)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro),
         config._make_repo('%s-updates' % basedistro)]
      )
    )

class Test_PkglistBug86_2(PkglistEventTestCase):
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug86_2', basedistro, True)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro),
         config._make_repo('%s-updates' % basedistro)]
      )
    )

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.clean_event_md(self.event._getroot().get('release-rpm'))

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug86_1')
    count2 = self.getPkglistCount('bug86_2')
    self.failUnless(count1 == count2, "bug86_1: %d packages; bug86_2: %d packages" % \
                      (count1, count2))

class Test_PkglistBug108_1(PkglistEventTestCase):
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug108_1', basedistro, True)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro)]
      )
    )
    config.add_config_section(
      self.conf,
      """
      <comps>
        <core>
          <package>gaim</package>
        </core>
      </comps>
      """
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
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'bug108_2', basedistro, False)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro),
         config._make_repo('%s-updates' % basedistro)]
      )
    )
    config.add_config_section(
      self.conf,
      """
      <comps>
        <core>
          <package>gaim</package>
        </core>
      </comps>
      """
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

    self.failUnless(found_pidgin or found_libpurple)
    self.failIf(found_gaim)

class Test_Supplied(DummyPkglistEventTestCase):
  "pkglist supplied"
  _conf = "<pkglist>pkglist/pkglist</pkglist>"

  def __init__(self, basedistro):
    EventTestCase.__init__(self, basedistro=basedistro)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    pkglist_in  = (pps.Path(__file__).dirname.dirname /
                   self.event.config.get('text()')).read_lines()
    pkglist_out = self.event.cvars['pkglist']
    self.failUnlessEqual(sorted(pkglist_in), sorted(pkglist_out))

class Test_PackageAdded(PkglistEventTestCase):
  "added package"
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'pkgadded', basedistro, True)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro),
         xmllib.config.read(StringIO("<repofile>pkglist/pkglist-test-repos1.repo</repofile>"))]
      )
    )
    config.add_config_section(
      self.conf,
      """
      <comps>
        <core>
          <package>pkglist-test-package1</package>
        </core>
      </comps>
      """
    )

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package1-1.0-1' in self.event.cvars['pkglist'])

class Test_ObsoletedPackage(PkglistEventTestCase):
  "obsoleted package"
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'pkgobsoleted', basedistro, False)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro),
         xmllib.config.read(StringIO("<repofile>pkglist/pkglist-test-repos1.repo</repofile>")),
         xmllib.config.read(StringIO("<repofile>pkglist/pkglist-test-repos2.repo</repofile>"))]
      )
    )
    config.add_config_section(
      self.conf,
      """
      <comps>
        <core>
          <package>pkglist-test-package2</package>
        </core>
      </comps>
      """
    )

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package2-1.0-1' in self.event.cvars['pkglist'])
    self.failIf('pkglist-test-package1-1.0-1' in self.event.cvars['pkglist'])

class Test_RemovedPackage(PkglistEventTestCase):
  "removed package"
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'pkgremoved', basedistro, False)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failIf('pkglist-test-package2-1.0-1' in self.event.cvars['pkglist'])

class Test_ExclusivePackage_1(PkglistEventTestCase):
  "test-package required only by another test-package"
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'exclusive_1', basedistro, False)
    config.add_config_section(
      self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro),
         xmllib.config.read(StringIO("<repofile>pkglist/pkglist-test-repos3.repo</repofile>"))]
      )
    )
    config.add_config_section(
      self.conf,
      """
      <comps>
        <core>
          <package>pkglist-test-package3</package>
        </core>
      </comps>
      """
    )

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package3-1.0-1' in self.event.cvars['pkglist'])
    self.failUnless('pkglist-test-package4-1.0-1' in self.event.cvars['pkglist'])

class Test_ExclusivePackage_2(PkglistEventTestCase):
  "package not required by anything else not in pkglist"
  def __init__(self, basedistro):
    PkglistEventTestCase.__init__(self, 'exclusive_2', basedistro, False)

  def setUp(self):
    PkglistEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failIf('pkglist-test-package3-1.0-1' in self.event.cvars['pkglist'])
    self.failIf('pkglist-test-package4-1.0-1' in self.event.cvars['pkglist'])

def make_suite(basedistro):
  suite = ModuleTestSuite('pkglist')

  # core tests
  suite.addTest(make_core_suite(DummyPkglistEventTestCase, basedistro))

  # bug 84
  bug84 = ModuleTestSuite('pkglist')
  bug84.addTest(Test_PkglistBug84_1(basedistro))
  bug84.addTest(Test_PkglistBug84_2(basedistro))
  bug84.addTest(Test_PkglistBug84_3(basedistro))
  suite.addTest(bug84)

  # bug 85
  bug85 = ModuleTestSuite('pkglist')
  bug85.addTest(Test_PkglistBug85_1(basedistro))
  bug85.addTest(Test_PkglistBug85_2(basedistro))
  bug85.addTest(Test_PkglistBug85_3(basedistro))
  suite.addTest(bug85)

  # bug 86
  bug86 = ModuleTestSuite('pkglist')
  bug86.addTest(Test_PkglistBug86_1(basedistro))
  bug86.addTest(Test_PkglistBug86_2(basedistro))
  suite.addTest(bug86)

  # bug 108; for centos-5 base distro only
  if basedistro == 'centos-5':
    bug108 = ModuleTestSuite('pkglist')
    bug108.addTest(Test_PkglistBug108_1('centos-5'))
    bug108.addTest(Test_PkglistBug108_2('centos-5'))
    suite.addTest(bug108)

  # pkglist supplied
  suite.addTest(Test_Supplied(basedistro))

  # package added, obsoleted, and removed
  suite.addTest(Test_PackageAdded(basedistro))
  suite.addTest(Test_ObsoletedPackage(basedistro))
  suite.addTest(Test_RemovedPackage(basedistro))

  # add package that requires a package nothing else requires,
  # then remove it.
  suite.addTest(Test_ExclusivePackage_1(basedistro))
  suite.addTest(Test_ExclusivePackage_2(basedistro))

  return suite
