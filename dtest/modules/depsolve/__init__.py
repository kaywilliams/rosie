#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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

from deploy.util import pps
from deploy.util import rxml

from deploy.constants import KERNELS

from deploy.errors import DeployError

from dtest      import EventTestCase, ModuleTestSuite, _run_make
from dtest.core import make_core_suite

class DummyDepsolveEventTestCase(EventTestCase):
  moduleid = 'depsolve'
  eventid  = 'depsolve'
  _type = 'package'

  def setUp(self):
    EventTestCase.setUp(self)

class DepsolveEventTestCase(EventTestCase):
  moduleid = 'depsolve'
  eventid  = 'depsolve'
  _type = 'package'

  caseid = None
  clean  = False

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
    pkgfiles = []
    for repo in self.event.cvars['pkglist'].itervalues():
      pkgfiles.extend(pps.path(x.remote_path).basename 
                      for x in repo.itervalues())
    return pkgfiles


class Test_PackageAdded(DepsolveEventTestCase):
  "Package Added"
  _conf = """<packages>
    <package>depsolve-test-package1</package>
  </packages>"""
  caseid = 'pkgadded'
  clean  = True

  def _make_repos_config(self):
    repos = EventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='/tmp/dtest/depsolve-test-repos1.repo'))

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
    repos = EventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='/tmp/dtest/depsolve-test-repos1.repo'))
    repos.append(rxml.config.Element('repofile',
                 text='/tmp/dtest/depsolve-test-repos2.repo'))

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
    repos = EventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='/tmp/dtest/depsolve-test-repos3.repo'))

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
    repos = EventTestCase._make_repos_config(self)

    repos.append(rxml.config.Element('repofile',
                 text='/tmp/dtest/depsolve-test-repos6.repo'))
    return repos

  def setUp(self):
    DepsolveEventTestCase.setUp(self)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)

class Test_PackagePatterns(DepsolveEventTestCase):
  "Package patterns"
  _conf = ["""<config-rpms>
  <config-rpm id='test'>
  <requires>package1 = 1.0-1</requires>
  </config-rpm>
  </config-rpms>
  """,
  """
  <packages>
    <package>package*</package>
  </packages>"""]


  def _make_repos_config(self):
    repos = EventTestCase._make_repos_config(self)

    rxml.config.Element('repofile', text='shared/test-repos.repo', parent=repos)

    return repos

  def runTest(self):
    self.tb.dispatch.execute(until='depsolve')
    self.failUnless('package2-1.0-1.noarch.rpm' in self.getPkgFiles())
    self.failUnless('package1-1.0-1.noarch.rpm' in self.getPkgFiles())
    self.failIf('package1-1.0-2.noarch.rpm' in self.getPkgFiles())


class CompsEventTestCase(DummyDepsolveEventTestCase):
  _type = 'system'
  _conf = "<packages><package>kernel</package></packages>"

  def __init__(self, os, version, arch, conf=None):
    EventTestCase.__init__(self, os, version, arch, conf)
    self.included_groups = []
    self.included_pkgs = []
    self.excluded_pkgs = []

  def read_groupfile(self):
    return rxml.tree.parse(self.event.compsfile).getroot()

  def check_all(self, groupfile):
    self.check_core(groupfile)
    self.check_category(groupfile)
    self.check_excluded(groupfile)

  def check_core(self, groupfile):
    #still need to check if packages from included_groups in core

    packages = groupfile.xpath('/comps/group[\'core\']/packagelist/packagereq/text()')
    for pkg in self.included_pkgs:
      self.failUnless(pkg in packages, '%s not in %s' % (pkg, packages))

    kfound = False
    for kernel in KERNELS:
      if kernel in packages:
        kfound = True; break
    self.failUnless(kfound)

  def check_category(self, groupfile):
    self.failUnlessEqual(
      sorted(groupfile.xpath('/comps/category/grouplist/groupid/text()')),
      sorted(['core'])
    )

  def check_excluded(self, groupfile):
    pkgs = groupfile.xpath('/comps/group/packagelist/packagreq/text()')
    for pkg in self.excluded_pkgs:
      self.failIf(pkg in pkgs)

class Test_IncludePackages(CompsEventTestCase):
  "groupfile generated, groups included in core, kernel unlisted"

  def __init__(self, os, version, arch, conf=None):
    CompsEventTestCase.__init__(self, os, version, arch, conf=conf)
    self._add_config({ 
    'el6': \
    """<packages>
      <group>core</group>
      <group>base</group>
      <package>createrepo</package>
      <package>httpd</package>
    </packages>""",
    'el7': \
    """<packages>
      <group>core</group>
      <group>base</group>
      <package>createrepo</package>
      <package>httpd</package>
    </packages>""",
    'fc19': \
    """<packages>
      <group>core</group>
      <group>standard</group>
      <package>createrepo</package>
      <package>httpd</package>
    </packages>""",
    }[self.norm_os])

  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)

    groupfile = self.read_groupfile()

    self.included_pkgs = ['createrepo', 'httpd']
    self.check_all(groupfile)

class Test_IncludeGroupsAndPackages(CompsEventTestCase):
  "groupfile generated, groups and packages included"
  def __init__(self, os, version, arch, conf=None):
    CompsEventTestCase.__init__(self, os, version, arch, conf=conf)
    self._add_config({ 
    'el6': \
    """<packages>
      <group>base</group>
      <group>console-internet</group>
    </packages>""",
    'el7': \
    """<packages>
      <group>base</group>
      <group>web-server</group>
    </packages>""",
    'fc19': \
    """<packages>
      <group>standard</group>
      <group>web-server</group>
    </packages>""",
    }[self.norm_os])

  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)

    self.check_all(self.read_groupfile())

class Test_ExcludePackages(CompsEventTestCase):
  "groupfile generated, packages excluded"
  _conf = \
  """<packages>
    <group>core</group>
    <package>httpd</package>
    <exclude>httpd</exclude> 
  </packages>"""

  def setUp(self):
    CompsEventTestCase.setUp(self)
    self.event.cvars['excluded-packages'] = ['authconfig'] 

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)

class Test_GroupsByRepo(CompsEventTestCase):
  "groupfile generated, group included from specific repo"
  def __init__(self, os, version, arch, conf=None):
    CompsEventTestCase.__init__(self, os, version, arch, conf=conf)
    self._add_config({ 
    'el6':
    """<packages>
      <group repoid="base">core</group>
      <group>base</group>
      <group repoid="base">console-internet</group>
    </packages>""",
    'el7':
    """<packages>
      <group repoid="base">core</group>
      <group>base</group>
      <group repoid="base">web-server</group>
    </packages>""",
    'fc19': 
    """<packages>
      <group repoid="base">core</group>
      <group>standard</group>
      <group repoid="base">web-server</group>
    </packages>""",
    }[self.norm_os])

  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)

    self.check_all(self.read_groupfile())

    # still need to check 'core' and 'printing' came from 'base' #!

class Test_MultipleGroupfiles(CompsEventTestCase):
  "groupfile generated, multiple repositories with groupfiles"

  def __init__(self, os, version, arch, conf=None):
    CompsEventTestCase.__init__(self, os, version, arch, conf=conf)
    self._add_config({ 
    'el6': \
    """<packages>
      <group>base</group>
      <group>base-x</group>
    </packages>""",
    'el7': \
    """<packages>
      <group>base</group>
      <group>base-x</group>
    </packages>""",
    'fc19': \
    """<packages>
      <group>standard</group>
      <group>base-x</group>
    </packages>""",
    }[self.norm_os])

  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)

    self.check_all(self.read_groupfile())

    # still need to check that 'base-x' contains all packages listed in #!
    # both 'base' and 'livna' groupfiles in 'base-x' group #!



def make_suite(os, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname)

  suite = ModuleTestSuite('depsolve')

  # core tests
  suite.addTest(make_core_suite(DummyDepsolveEventTestCase, os, version, arch))

  # package added, obsoleted, and removed
  suite.addTest(Test_PackageAdded(os, version, arch))
  suite.addTest(Test_ObsoletedPackage(os, version, arch))
  suite.addTest(Test_RemovedPackage(os, version, arch))

  # add package that requires a package nothing else requires,
  # then remove it.
  suite.addTest(Test_ExclusivePackage_1(os, version, arch))
  suite.addTest(Test_ExclusivePackage_2(os, version, arch))

  # conflicting packages
  suite.addTest(Test_ConflictingPackages(os, version, arch))

  # package patterns
  suite.addTest(Test_PackagePatterns(os, version, arch))

  # comps tests
  suite.addTest(Test_IncludePackages(os, version, arch))
  suite.addTest(Test_IncludeGroupsAndPackages(os, version, arch))
  suite.addTest(Test_ExcludePackages(os, version, arch))
  suite.addTest(Test_GroupsByRepo(os, version, arch))
  ##suite.addTest(Test_MultipleGroupfiles(os, version, arch))
  return suite
