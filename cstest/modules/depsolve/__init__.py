#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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
import unittest

from centosstudio.util import pps
from centosstudio.util import repo
from centosstudio.util import rxml

from centosstudio.constants import KERNELS

from centosstudio.errors import CentOSStudioError

from cstest      import EventTestCase, ModuleTestSuite, _run_make
from cstest.core import make_core_suite

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

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    count = 0
    for tups in self.event.cvars['pkglist'].itervalues():
      count = count + len(tups)
    self.PKGLIST_COUNT[self.caseid] = count 

  def getPkglistCount(self, caseid):
    return self.PKGLIST_COUNT.get(caseid)

  def getPkgFiles(self):
    pkgtups = []
    for tups in self.event.cvars['pkglist'].itervalues():
      pkgtups.extend(tups)
    pkgfiles = []
    for tup in pkgtups:
       _, _, f, _, _ = tup
       pkgfiles.append(pps.path(f).basename) 
    return pkgfiles

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')

    for repoid in ['base', 'updates', 'everything']:
      if repoid in self.repos:
        r = repo.getDefaultRepoById(repoid, distro=self.distro,
                                            version=self.version,
                                            arch=self.arch,
                                            include_baseurl=True,
                                            baseurl='http://www.centossolutions.com/mirrors/%s' % self.distro)
        r.update({'mirrorlist': None, 'gpgkey': None, 'gpgcheck': None})
        if repoid == 'updates' and 'systemid' in r:
          # look for systemid in cstest folder 
          r['systemid'] = (pps.path(('/').join(__file__.split('/')[:-3]))
                           /pps.path(r['systemid']).basename)
        repos.append(r.toxml())

    return repos

class Test_PackageAdded(DepsolveEventTestCase):
  "Package Added"
  _conf = """<packages>
    <package>depsolve-test-package1</package>
  </packages>"""
  caseid = 'pkgadded'
  clean  = True

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='/tmp/cstest/depsolve-test-repos1.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failUnless('depsolve-test-package1-1.0-1.noarch.rpm' in self.getPkgFiles())

class Test_ObsoletedPackage(DepsolveEventTestCase):
  "Package obsoleted"
  _conf = """<packages>
    <package>depsolve-test-package2</package>
  </packages>"""

  caseid = 'pkgobsoleted'

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='/tmp/cstest/depsolve-test-repos1.repo'))
    repos.append(rxml.config.Element('repofile',
                 text='/tmp/cstest/depsolve-test-repos2.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failUnless('depsolve-test-package2-1.0-1.noarch.rpm' in self.getPkgFiles())
    self.failIf('depsolve-test-package1-1.0-1.noarch.rpm' in self.getPkgFiles())

class Test_RemovedPackage(DepsolveEventTestCase):
  "Package removed"
  caseid = 'pkgremoved'

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failIf('depsolve-test-package2-1.0-1.noarch.rpm' in self.getPkgFiles())

class Test_ExclusivePackage_1(DepsolveEventTestCase):
  "A package is required by only one other package..."
  _conf = """<packages>
    <package>depsolve-test-package3</package>
  </packages>"""
  caseid = 'exclusive_1'

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='/tmp/cstest/depsolve-test-repos3.repo'))

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failUnless('depsolve-test-package3-1.0-1.noarch.rpm' in self.getPkgFiles())
    self.failUnless('depsolve-test-package4-1.0-1.noarch.rpm' in self.getPkgFiles())

class Test_ExclusivePackage_2(DepsolveEventTestCase):
  "...and it should go away now"
  caseid = 'exclusive_2'

  def setUp(self):
    DepsolveEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failIf('depsolve-test-package3-1.0-1.noarch.rpm' in self.getPkgFiles())
    self.failIf('depsolve-test-package4-1.0-1.noarch.rpm' in self.getPkgFiles())

class Test_ConflictingPackages(DepsolveEventTestCase):
  "error with conflicting packages"
  caseid = 'conflicting_package'
  _conf = """<packages>
    <package>package1</package>
    <package>package2</package>
  </packages>"""

  def _make_repos_config(self):
    repos = DepsolveEventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='/tmp/cstest/depsolve-test-repos6.repo'))
    return repos

  def setUp(self):
    DepsolveEventTestCase.setUp(self)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(CentOSStudioError, self.event)


def make_suite(distro, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname)

  suite = ModuleTestSuite('depsolve')

  # core tests
  suite.addTest(make_core_suite(DummyDepsolveEventTestCase, distro, version, arch))

  # package added, obsoleted, and removed
  suite.addTest(Test_PackageAdded(distro, version, arch))
  suite.addTest(Test_ObsoletedPackage(distro, version, arch))
  suite.addTest(Test_RemovedPackage(distro, version, arch))

  # add package that requires a package nothing else requires,
  # then remove it.
  suite.addTest(Test_ExclusivePackage_1(distro, version, arch))
  suite.addTest(Test_ExclusivePackage_2(distro, version, arch))

  # conflicting packages
  suite.addTest(Test_ConflictingPackages(distro, version, arch))

  return suite
