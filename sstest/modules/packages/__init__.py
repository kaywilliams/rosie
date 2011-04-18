#
# Copyright (c) 2011
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
from systemstudio.util import pps
from systemstudio.util import rxml

from systemstudio.constants import KERNELS

from sstest      import EventTestCase, ModuleTestSuite
from sstest.core import make_core_suite

class PackagesEventTestCase(EventTestCase):
  moduleid = 'packages'
  eventid  = 'packages'

class _PackagesEventTestCase(PackagesEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    PackagesEventTestCase.__init__(self, distro, version, arch, conf)
    self.included_groups = []
    self.included_pkgs = []
    self.excluded_pkgs = []

  def setUp(self):
    PackagesEventTestCase.setUp(self)
    self.clean_event_md()

  def read_groupfile(self):
    return rxml.tree.parse(self.event.cvars['groupfile']).getroot()

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

class Test_IncludePackages(_PackagesEventTestCase):
  "groupfile generated, groups included in core, kernel unlisted"
  _conf = \
  """<packages>
    <group>core</group>
    <group>base</group>
  </packages>"""

  def runTest(self):
    self.tb.dispatch.execute(until='packages')

    groupfile = self.read_groupfile()

    self.check_all(groupfile)

class Test_IncludeCoreGroups(_PackagesEventTestCase):
  "groupfile generated, packages included in $NAME-packages"
  _conf = \
  """<packages>
    <group>core</group>
    <package>createrepo</package>
    <package>httpd</package>
  </packages>"""

  def setUp(self):
    _PackagesEventTestCase.setUp(self)
    self.event.cvars['required-packages'] = set(['kde', 'xcalc'])

  def runTest(self):
    self.tb.dispatch.execute(until='packages')

    self.included_pkgs = ['createrepo', 'httpd', 'kde', 'xcalc']
    self.check_all(self.read_groupfile())

class Test_IncludeGroups(_PackagesEventTestCase):
  "groupfile generated, groups included"
  _conf = \
  """<packages>
    <group>base</group>
    <group>printing</group>
  </packages>"""

  def runTest(self):
    self.tb.dispatch.execute(until='packages')

    self.check_all(self.read_groupfile())

class Test_ExcludePackages(_PackagesEventTestCase):
  "groupfile generated, packages excluded"
  _conf = \
  """<packages>
    <group>core</group>
    <exclude>cpio</exclude>
    <exclude>kudzu</exclude>
  </packages>"""

  def setUp(self):
    _PackagesEventTestCase.setUp(self)
    self.event.cvars['excluded-packages'] = set(['passwd', 'setup'])

  def runTest(self):
    self.tb.dispatch.execute(until='packages')

    self.excluded_pkgs = ['cpio', 'kudzu', 'passwd', 'setup']
    self.check_all(self.read_groupfile())

class Test_GroupsByRepo(_PackagesEventTestCase):
  "groupfile generated, group included from specific repo"
  _conf = \
  """<packages>
    <group repoid="base">core</group>
    <group>base</group>
    <group repoid="base">printing</group>
  </packages>"""

  def runTest(self):
    self.tb.dispatch.execute(until='packages')

    self.check_all(self.read_groupfile())

    # still need to check 'core' and 'printing' came from 'base' #!

class Test_MultipleGroupfiles(_PackagesEventTestCase):
  "groupfile generated, multiple repositories with groupfiles"
  _conf = \
  """<packages>
    <group repoid="base">core</groups>
    <group>base-x</group>
  </packages>"""

  def runTest(self):
    self.tb.dispatch.execute(until='packages')

    self.check_all(self.read_groupfile())

    # still need to check that 'base-x' contains all packages listed in #!
    # both 'base' and 'livna' groupfiles in 'base-x' group #!

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('packages')

  suite.addTest(make_core_suite(PackagesEventTestCase, distro, version, arch))
  suite.addTest(Test_IncludePackages(distro, version, arch))
  suite.addTest(Test_IncludeCoreGroups(distro, version, arch))
  suite.addTest(Test_IncludeGroups(distro, version, arch))
  suite.addTest(Test_ExcludePackages(distro, version, arch))
  suite.addTest(Test_GroupsByRepo(distro, version, arch))
  ##suite.addTest(Test_MultipleGroupfiles(distro, version, arch))

  return suite
