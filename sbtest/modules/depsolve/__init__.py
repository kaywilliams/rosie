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

from systembuildertest      import EventTestCase, ModuleTestSuite, _run_make
from systembuildertest.core import make_core_suite

class DummyDepsolveEventTestCase(EventTestCase):
  moduleid = 'depsolve'
  eventid  = 'depsolve'

class DepsolveEventTestCase(EventTestCase):
  moduleid = 'depsolve'
  eventid  = 'depsolve'

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
    self.tb.dispatch.execute(until='depsolve')
    self.PKGLIST_COUNT[self.caseid] = len(self.event.cvars['pkglist'])

  def getPkglistCount(self, caseid):
    return self.PKGLIST_COUNT.get(caseid)

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')

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

class Test_DepsolveBug84_1(DepsolveEventTestCase):
  "Bug 84 #1: Force 'depsolve' without base group"
  caseid = 'bug84_1'
  clean  =  True

class Test_DepsolveBug84_2(DepsolveEventTestCase):
  "Bug 84 #2: Run 'depsolve' with base group"
  "with base group"
  _conf = """<packages>
    <group>base</group>
  </packages>"""
  caseid = 'bug84_2'

class Test_DepsolveBug84_3(DepsolveEventTestCase):
  "Bug 84 #3: Run 'depsolve' without base group"
  caseid = 'bug84_3'

  def runTest(self):
    DepsolveEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug84_1')
    count2 = self.getPkglistCount('bug84_3')
    self.failUnless(count1 == count2,
      "incremental depsolve: %d, forced depsolve: %d" % (count1, count2))

class Test_DepsolveBug85_1(DepsolveEventTestCase):
  "Bug 85 #1: Force 'depsolve' without updates repository"
  caseid = 'bug85_1'
  clean  = True

class Test_DepsolveBug85_2(DepsolveEventTestCase):
  "Bug 85 #2: Run 'depsolve' with updates repository"
  caseid = 'bug85_2'
  repos = ['base', 'updates']

class Test_DepsolveBug85_3(DepsolveEventTestCase):
  "Bug 85 #3: Run 'depsolve' without updates repository"
  caseid = 'bug85_3'

  def runTest(self):
    DepsolveEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug85_1')
    count2 = self.getPkglistCount('bug85_3')
    self.failUnless(count1 == count2, "bug85_1: %d packages; bug85_3: %d packages" % \
                    (count1, count2))

class Test_DepsolveBug86_1(DepsolveEventTestCase):
  "Bug 86 #1: Force 'depsolve' without 'release-rpm' forced"
  caseid = 'bug86_1'
  clean  = True
  repos = ['base', 'updates']

class Test_DepsolveBug86_2(DepsolveEventTestCase):
  "Bug 86 #2: Force 'depsolve' with 'release-rpm' events"
  caseid = 'bug86_2'
  clean  = True
  repos = ['base', 'updates']

  def setUp(self):
    DepsolveEventTestCase.setUp(self)
    self.clean_event_md(self.event._getroot().get('release-rpm'))

  def runTest(self):
    DepsolveEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug86_1')
    count2 = self.getPkglistCount('bug86_2')
    self.failUnless(count1 == count2, "bug86_1: %d packages; bug86_2: %d packages" % \
                      (count1, count2))

class Test_DepsolveBug108(DepsolveEventTestCase):
  "Bug 108: 'pidgin' or 'libpurple' should be in pkglist (CentOS5-only test)"
  _conf = """<packages>
    <package>gaim</package>
  </packages>"""
  caseid = 'bug108'
  clean  = False
  repos  = ['base', 'updates']

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
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

class Test_DepsolveBug163_1(DepsolveEventTestCase):
  "Bug 163 #1: Newer package is not the desired package"
  _conf = """<packages>
    <package>depsolve-bug163-req</package>
  </packages>"""
  caseid = 'bug163_1'
  clean  = True

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='depsolve/depsolve-test-repos4.repo'))
    return repos

  def runTest(self):
    DepsolveEventTestCase.runTest(self)
    self.failUnless('depsolve-bug163-prov-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failIf('depsolve-bug163-prov-2.0-1.noarch' in self.event.cvars['pkglist'])

class Test_DepsolveBug163_2(DepsolveEventTestCase):
  "Bug 163 #2: Newer package is not brought down when 'release-rpm' is forced"
  _conf = """<packages>
    <package>depsolve-bug163-req</package>
  </packages>"""
  caseid = 'bug163_2'
  clean  = False

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='depsolve/depsolve-test-repos4.repo'))
    return repos

  def setUp(self):
    DepsolveEventTestCase.setUp(self)
    self.clean_event_md(self.event._getroot().get('release-rpm'))

  def runTest(self):
    DepsolveEventTestCase.runTest(self)
    count1 = self.getPkglistCount('bug163_1')
    count2 = self.getPkglistCount('bug163_2')
    self.failUnless(count1 == count2, "bug163_1: %d packages; bug163_2: %d packages" % \
                      (count1, count2))
    self.failUnless('depsolve-bug163-prov-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failIf('depsolve-bug163-prov-2.0-1.noarch' in self.event.cvars['pkglist'])

class Test_Supplied(DummyDepsolveEventTestCase):
  "Package list file is supplied"
  _conf = "<depsolve>depsolve/depsolve</depsolve>"

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    depsolve_in  = (pps.path(__file__).abspath().dirname.dirname /
                   self.event.config.get('text()')).read_lines()
    depsolve_out = self.event.cvars['pkglist']
    self.failUnlessEqual(sorted(depsolve_in), sorted(depsolve_out))

class Test_PackageAdded(DepsolveEventTestCase):
  "Misc. Test #1: Package Added"
  _conf = """<packages>
    <package>depsolve-test-package1</package>
  </packages>"""
  caseid = 'pkgadded'
  clean  = True

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='depsolve/depsolve-test-repos1.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failUnless('depsolve-test-package1-1.0-1.noarch' in self.event.cvars['pkglist'])

class Test_ObsoletedPackage(DepsolveEventTestCase):
  "Misc. Test #2: Package obsoleted"
  _conf = """<packages>
    <package>depsolve-test-package2</package>
  </packages>"""

  caseid = 'pkgobsoleted'

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='depsolve/depsolve-test-repos1.repo'))
    repos.append(rxml.config.Element('repofile',
                 text='depsolve/depsolve-test-repos2.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failUnless('depsolve-test-package2-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failIf('depsolve-test-package1-1.0-1.noarch' in self.event.cvars['pkglist'])

class Test_RemovedPackage(DepsolveEventTestCase):
  "Misc. Test #3: Package removed"
  caseid = 'pkgremoved'

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failIf('depsolve-test-package2-1.0-1.noarch' in self.event.cvars['pkglist'])

class Test_ExclusivePackage_1(DepsolveEventTestCase):
  "Misc. Test #4: A package is required by only one other package..."
  _conf = """<packages>
    <package>depsolve-test-package3</package>
  </packages>"""
  caseid = 'exclusive_1'

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='depsolve/depsolve-test-repos3.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failUnless('depsolve-test-package3-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failUnless('depsolve-test-package4-1.0-1.noarch' in self.event.cvars['pkglist'])

class Test_ExclusivePackage_2(DepsolveEventTestCase):
  "Misc. Test #4 (contd.): ...and it should go away now"
  caseid = 'exclusive_2'

  def setUp(self):
    DepsolveEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failIf('depsolve-test-package3-1.0-1.noarch' in self.event.cvars['pkglist'])
    self.failIf('depsolve-test-package4-1.0-1.noarch' in self.event.cvars['pkglist'])

def make_suite(distro, version, arch):
  _run_make(pps.path(__file__).dirname)

  suite = ModuleTestSuite('depsolve')

  # core tests
  suite.addTest(make_core_suite(DummyDepsolveEventTestCase, distro, version, arch))

  # bug 84
  bug84 = ModuleTestSuite('depsolve')
  bug84.addTest(Test_DepsolveBug84_1(distro, version, arch))
  bug84.addTest(Test_DepsolveBug84_2(distro, version, arch))
  bug84.addTest(Test_DepsolveBug84_3(distro, version, arch))
  suite.addTest(bug84)

  # bug 85
  bug85 = ModuleTestSuite('depsolve')
  bug85.addTest(Test_DepsolveBug85_1(distro, version, arch))
  bug85.addTest(Test_DepsolveBug85_2(distro, version, arch))
  bug85.addTest(Test_DepsolveBug85_3(distro, version, arch))
  suite.addTest(bug85)

  # bug 86
  bug86 = ModuleTestSuite('depsolve')
  bug86.addTest(Test_DepsolveBug86_1(distro, version, arch))
  bug86.addTest(Test_DepsolveBug86_2(distro, version, arch))
  suite.addTest(bug86)

  # bug 108; for centos-5 base distro only
  if distro == 'centos' and version == '5':
    bug108 = ModuleTestSuite('depsolve')
    bug108.addTest(Test_DepsolveBug108(distro, version, arch))
    suite.addTest(bug108)

  # bug 163
  bug163 = ModuleTestSuite('depsolve')
  bug163.addTest(Test_DepsolveBug163_1(distro, version, arch))
  bug163.addTest(Test_DepsolveBug163_2(distro, version, arch))
  suite.addTest(bug163)

  # package added, obsoleted, and removed
  suite.addTest(Test_PackageAdded(distro, version, arch))
  suite.addTest(Test_ObsoletedPackage(distro, version, arch))
  suite.addTest(Test_RemovedPackage(distro, version, arch))

  # add package that requires a package nothing else requires,
  # then remove it.
  suite.addTest(Test_ExclusivePackage_1(distro, version, arch))
  suite.addTest(Test_ExclusivePackage_2(distro, version, arch))

  return suite
