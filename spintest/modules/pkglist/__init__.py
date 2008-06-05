#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
from StringIO import StringIO

import unittest

from rendition import pps
from rendition import repo
from rendition import rxml

from spintest      import EventTestCase, ModuleTestSuite, _run_make
from spintest.core import make_core_suite

class DummyPkglistEventTestCase(EventTestCase):
  moduleid = 'pkglist'
  eventid  = 'pkglist'

class PkglistEventTestCase(EventTestCase):
  moduleid = 'pkglist'
  eventid  = 'pkglist'

  caseid = None
  clean  = False

  repos = ['base'] # list of repos to include

  PKGLIST_COUNT = {}

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

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')

    if self.distro == 'redhat' and self.version == '5Server':
      if 'base' in self.repos:
        # base repo
        base = rxml.config.Element('repo', attrs={'id': 'base'}, parent=repos)
        rxml.config.Element('baseurl', parent=base,
                            text='http://www.renditionsoftware.com/mirrors/redhat/'
                            'enterprise/5Server/en/os/i386/Server')
        rxml.config.Element('name', text='base', parent=base)

      if 'updates' in self.repos:
        # updates repo
        updates = rxml.config.Element('repo', attrs={'id': 'updates'}, parent=repos)
        rxml.config.Element('baseurl', parent=updates,
                            text='rhns:///rhel-i386-server-5')
        rxml.config.Element('name', text='updates', parent=updates)
        rxml.config.Element('systemid', text='/etc/sysconfig/rhn/systemid', parent=updates)

    else:

      for repoid in ['base', 'updates', 'everything']:
        if repoid in self.repos:
          r = repo.getDefaultRepoById(repoid, distro=self.distro,
                                              version=self.version,
                                              arch=self.arch,
                                              include_baseurl=True,
                                              baseurl='http://www.renditionsoftware.com/mirrors/%s' % self.distro)
          r.update({'mirrorlist': None, 'gpgkey': None, 'gpgcheck': 'no'})
          repos.append(r.toxml())

    return repos

class Test_PkglistBug84_1(PkglistEventTestCase):
  "Bug 84 #1: Force 'pkglist' without base group"
  caseid = 'bug84_1'
  clean  =  True

class Test_PkglistBug84_2(PkglistEventTestCase):
  "Bug 84 #2: Run 'pkglist' with base group"
  "with base group"
  _conf = """<comps>
    <group>base</group>
  </comps>"""
  caseid = 'bug84_2'

class Test_PkglistBug84_3(PkglistEventTestCase):
  "Bug 84 #3: Run 'pkglist' without base group"
  caseid = 'bug84_3'

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug84_1')
    count2 = self.getPkglistCount('bug84_3')
    self.failUnless(count1 == count2,
      "incremental depsolve: %d, forced depsolve: %d" % (count1, count2))

class Test_PkglistBug85_1(PkglistEventTestCase):
  "Bug 85 #1: Force 'pkglist' without updates repository"
  caseid = 'bug85_1'
  clean  = True

class Test_PkglistBug85_2(PkglistEventTestCase):
  "Bug 85 #2: Run 'pkglist' with updates repository"
  caseid = 'bug85_2'
  repos = ['base', 'updates']

class Test_PkglistBug85_3(PkglistEventTestCase):
  "Bug 85 #3: Run 'pkglist' without updates repository"
  caseid = 'bug85_3'

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug85_1')
    count2 = self.getPkglistCount('bug85_3')
    self.failUnless(count1 == count2, "bug85_1: %d packages; bug85_3: %d packages" % \
                    (count1, count2))

class Test_PkglistBug86_1(PkglistEventTestCase):
  "Bug 86 #1: Force 'pkglist' without 'release-rpm' forced"
  caseid = 'bug86_1'
  clean  = True
  repos = ['base', 'updates']

class Test_PkglistBug86_2(PkglistEventTestCase):
  "Bug 86 #2: Force 'pkglist' with 'release-rpm' events"
  caseid = 'bug86_2'
  clean  = True
  repos = ['base', 'updates']

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.clean_event_md(self.event._getroot().get('release-rpm'))

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug86_1')
    count2 = self.getPkglistCount('bug86_2')
    self.failUnless(count1 == count2, "bug86_1: %d packages; bug86_2: %d packages" % \
                      (count1, count2))

class Test_PkglistBug108(PkglistEventTestCase):
  "Bug 108: 'pidgin' or 'libpurple' should be in pkglist (CentOS5-only test)"
  _conf = """<comps>
    <package>gaim</package>
  </comps>"""
  caseid = 'bug108'
  clean  = False
  repos  = ['base', 'updates']

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

class Test_PkglistBug163_1(PkglistEventTestCase):
  "Bug 163 #1: Newer package is not the desired package"
  _conf = """<comps>
    <package>pkglist-bug163-req</package>
  </comps>"""
  caseid = 'bug163_1'
  clean  = True

  def _make_repos_config(self):
    repos = PkglistEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='pkglist/pkglist-test-repos4.repo'))
    return repos

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    self.failUnless('pkglist-bug163-prov-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failIf('pkglist-bug163-prov-2.0-1.noarch' in self.event.cvars['pkglist'])

class Test_PkglistBug163_2(PkglistEventTestCase):
  "Bug 163 #2: Newer package is not brought down when 'release-rpm' is forced"
  _conf = """<comps>
    <package>pkglist-bug163-req</package>
  </comps>"""
  caseid = 'bug163_2'
  clean  = False

  def _make_repos_config(self):
    repos = PkglistEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='pkglist/pkglist-test-repos4.repo'))
    return repos

  def setUp(self):
    PkglistEventTestCase.setUp(self)
    self.clean_event_md(self.event._getroot().get('release-rpm'))

  def runTest(self):
    PkglistEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug163_1')
    count2 = self.getPkglistCount('bug163_2')
    self.failUnless(count1 == count2, "bug163_1: %d packages; bug163_2: %d packages" % \
                      (count1, count2))
    self.failUnless('pkglist-bug163-prov-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failIf('pkglist-bug163-prov-2.0-1.noarch' in self.event.cvars['pkglist'])

class Test_Supplied(DummyPkglistEventTestCase):
  "Package list file is supplied"
  _conf = "<pkglist>pkglist/pkglist</pkglist>"

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    pkglist_in  = (pps.path(__file__).dirname.dirname /
                   self.event.config.get('text()')).read_lines()
    pkglist_out = self.event.cvars['pkglist']
    self.failUnlessEqual(sorted(pkglist_in), sorted(pkglist_out))

class Test_PackageAdded(PkglistEventTestCase):
  "Misc. Test #1: Package Added"
  _conf = """<comps>
    <package>pkglist-test-package1</package>
  </comps>"""
  caseid = 'pkgadded'
  clean  = True

  def _make_repos_config(self):
    repos = PkglistEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='pkglist/pkglist-test-repos1.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package1-1.0-1.noarch' in self.event.cvars['pkglist'])

class Test_ObsoletedPackage(PkglistEventTestCase):
  "Misc. Test #2: Package obsoleted"
  _conf = """<comps>
    <package>pkglist-test-package2</package>
  </comps>"""

  caseid = 'pkgobsoleted'

  def _make_repos_config(self):
    repos = PkglistEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='pkglist/pkglist-test-repos1.repo'))
    repos.append(rxml.config.Element('repofile',
                 text='pkglist/pkglist-test-repos2.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package2-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failIf('pkglist-test-package1-1.0-1.noarch' in self.event.cvars['pkglist'])

class Test_RemovedPackage(PkglistEventTestCase):
  "Misc. Test #3: Package removed"
  caseid = 'pkgremoved'

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failIf('pkglist-test-package2-1.0-1.noarch' in self.event.cvars['pkglist'])

class Test_ExclusivePackage_1(PkglistEventTestCase):
  "Misc. Test #4: A package is required by only one other package..."
  _conf = """<comps>
    <package>pkglist-test-package3</package>
  </comps>"""
  caseid = 'exclusive_1'

  def _make_repos_config(self):
    repos = PkglistEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='pkglist/pkglist-test-repos3.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failUnless('pkglist-test-package3-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failUnless('pkglist-test-package4-1.0-1.noarch' in self.event.cvars['pkglist'])

class Test_ExclusivePackage_2(PkglistEventTestCase):
  "Misc. Test #4 (contd.): ...and it should go away now"
  caseid = 'exclusive_2'

  def setUp(self):
    PkglistEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='pkglist')
    self.failIf('pkglist-test-package3-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failIf('pkglist-test-package4-1.0-1.noarch' in self.event.cvars['pkglist'])

def make_suite(distro, version, arch):
  _run_make(pps.path(__file__).dirname)

  suite = ModuleTestSuite('pkglist')

  # core tests
  suite.addTest(make_core_suite(DummyPkglistEventTestCase, distro, version, arch))

  # bug 84
  bug84 = ModuleTestSuite('pkglist')
  bug84.addTest(Test_PkglistBug84_1(distro, version, arch))
  bug84.addTest(Test_PkglistBug84_2(distro, version, arch))
  bug84.addTest(Test_PkglistBug84_3(distro, version, arch))
  suite.addTest(bug84)

  # bug 85
  bug85 = ModuleTestSuite('pkglist')
  bug85.addTest(Test_PkglistBug85_1(distro, version, arch))
  bug85.addTest(Test_PkglistBug85_2(distro, version, arch))
  bug85.addTest(Test_PkglistBug85_3(distro, version, arch))
  suite.addTest(bug85)

  # bug 86
  bug86 = ModuleTestSuite('pkglist')
  bug86.addTest(Test_PkglistBug86_1(distro, version, arch))
  bug86.addTest(Test_PkglistBug86_2(distro, version, arch))
  suite.addTest(bug86)

  # bug 108; for centos-5 base distro only
  if distro == 'centos' and version == '5':
    bug108 = ModuleTestSuite('pkglist')
    bug108.addTest(Test_PkglistBug108(distro, version, arch))
    suite.addTest(bug108)

  # bug 163
  bug163 = ModuleTestSuite('pkglist')
  bug163.addTest(Test_PkglistBug163_1(distro, version, arch))
  bug163.addTest(Test_PkglistBug163_2(distro, version, arch))
  suite.addTest(bug163)

  # pkglist supplied
  suite.addTest(Test_Supplied(distro, version, arch))

  # package added, obsoleted, and removed
  suite.addTest(Test_PackageAdded(distro, version, arch))
  suite.addTest(Test_ObsoletedPackage(distro, version, arch))
  suite.addTest(Test_RemovedPackage(distro, version, arch))

  # add package that requires a package nothing else requires,
  # then remove it.
  suite.addTest(Test_ExclusivePackage_1(distro, version, arch))
  suite.addTest(Test_ExclusivePackage_2(distro, version, arch))

  return suite
