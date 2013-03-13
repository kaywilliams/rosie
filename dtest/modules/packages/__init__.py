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

from dtest      import EventTestCase, ModuleTestSuite
from dtest.core import make_core_suite

from deploy.util import rxml

from deploy.constants import KERNELS

class PackagesEventTestCase(EventTestCase):
  moduleid = 'packages'
  eventid  = 'packages'
  _mode = 'package'

  _conf = "<packages><package>kernel</package></packages>"

class CompsEventTestCase(EventTestCase):
  moduleid = 'packages'
  eventid  = 'comps'
  _conf = "<packages><package>kernel</package></packages>"

  def __init__(self, os, version, arch, conf=None):
    EventTestCase.__init__(self, os, version, arch, conf)
    self.included_groups = []
    self.included_pkgs = []
    self.excluded_pkgs = []

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()

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
  _conf = \
  """<packages>
    <group>core</group>
    <group>base</group>
    <package>createrepo</package>
    <package>httpd</package>
  </packages>"""

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
    '5': \
    """<packages>
      <group>base</group>
      <group>printing</group>
    </packages>""",
    '6': \
    """<packages>
      <group>base</group>
      <group>console-internet</group>
    </packages>""",
    }[version[:1]])

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
    self.tb.dispatch.execute(until=self.event.id)

    self.excluded_pkgs = ['httpd', 'authconfig']
    self.check_all(self.read_groupfile())

class Test_GroupsByRepo(CompsEventTestCase):
  "groupfile generated, group included from specific repo"
  def __init__(self, os, version, arch, conf=None):
    CompsEventTestCase.__init__(self, os, version, arch, conf=conf)
    self._add_config({ 
    '5':
    """<packages>
      <group repoid="base">core</group>
      <group>base</group>
      <group repoid="base">printing</group>
    </packages>""",
    '6':
    """<packages>
      <group repoid="base">core</group>
      <group>base</group>
      <group repoid="base">console-internet</group>
    </packages>""",}[version[:1]])

  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)

    self.check_all(self.read_groupfile())

    # still need to check 'core' and 'printing' came from 'base' #!

class Test_MultipleGroupfiles(CompsEventTestCase):
  "groupfile generated, multiple repositories with groupfiles"
  _conf = \
  """<packages>
    <group repoid="base">core</groups>
    <group>base-x</group>
  </packages>"""

  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)

    self.check_all(self.read_groupfile())

    # still need to check that 'base-x' contains all packages listed in #!
    # both 'base' and 'livna' groupfiles in 'base-x' group #!


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('packages')

  suite.addTest(make_core_suite(PackagesEventTestCase, os, version, arch))
  suite.addTest(Test_IncludePackages(os, version, arch))
  suite.addTest(Test_IncludeGroupsAndPackages(os, version, arch))
  suite.addTest(Test_ExcludePackages(os, version, arch))
  suite.addTest(Test_GroupsByRepo(os, version, arch))
  ##suite.addTest(Test_MultipleGroupfiles(os, version, arch))

  return suite
