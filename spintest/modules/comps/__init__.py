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
from rendition import pps
from rendition import xmllib

from spin.modules.core.software.comps import KERNELS

from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class CompsEventTestCase(EventTestCase):
  moduleid = 'comps'
  eventid  = 'comps'

class _CompsEventTestCase(CompsEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    CompsEventTestCase.__init__(self, distro, version, arch, conf)
    self.included_groups = []
    self.included_pkgs = []
    self.excluded_pkgs = []

  def setUp(self):
    CompsEventTestCase.setUp(self)
    self.clean_event_md()

  def read_comps(self):
    return xmllib.tree.read(self.event.cvars['comps-file'])

  def check_all(self, comps):
    self.check_core(comps)
    self.check_category(comps)
    self.check_groups(comps)

  def check_core(self, comps):
    groups = comps.xpath('/comps/group/id/text()')
    for grp in self.included_groups:
      self.failUnless(grp in groups)

    packages = comps.xpath('/comps/group[id/text()="core"]/packagelist/packagereq/text()')
    for pkg in self.included_pkgs:
      self.failUnless(pkg in packages)

    kfound = False
    for kernel in KERNELS:
      if kernel in packages:
        kfound = True; break
    self.failUnless(kfound)

  def check_category(self, comps):
    self.failUnlessEqual(sorted(comps.xpath('/comps/category/grouplist/groupid/text()')),
                         sorted(self.included_groups))

  def check_groups(self, comps):
    pkgs = comps.xpath('/comps/group/packagelist/packagreq/text()')
    for pkg in self.excluded_pkgs:
      self.failIf(pkg in pkgs)

class Test_Supplied(_CompsEventTestCase):
  "comps supplied"
  _conf = "<comps>comps/comps.xml</comps>" # location needs adjustment when config moves

  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    comps_in  = xmllib.tree.read(pps.path(__file__).dirname/'comps.xml')
    comps_out = self.read_comps()

    self.failUnlessEqual(comps_in, comps_out)

class Test_IncludePackages(_CompsEventTestCase):
  "comps generated, groups included in core, kernel unlisted"
  _conf = \
  """<comps>
    <group>core</group>
    <group>base</group>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    comps = self.read_comps()

    self.included_groups = ['core', 'base']
    self.check_all(comps)

class Test_IncludeCoreGroups(_CompsEventTestCase):
  "comps generated, packages included in core"
  _conf = \
  """<comps>
    <group>core</group>
    <package>createrepo</package>
    <package>httpd</package>
  </comps>"""

  def setUp(self):
    _CompsEventTestCase.setUp(self)
    self.event.cvars['comps-included-packages'] = set(['kde', 'xcalc'])

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core']
    self.included_pkgs = ['createrepo', 'httpd', 'kde', 'xcalc']
    self.check_all(self.read_comps())

class Test_IncludeGroups(_CompsEventTestCase):
  "comps generated, groups included"
  _conf = \
  """<comps>
    <group>base</group>
    <group>printing</group>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base', 'printing']
    self.check_all(self.read_comps())

class Test_ExcludePackages(_CompsEventTestCase):
  "comps generated, packages excluded"
  _conf = \
  """<comps>
    <exclude-package>cpio</exclude-package>
    <exclude-package>kudzu</exclude-package>
  </comps>"""

  def setUp(self):
    _CompsEventTestCase.setUp(self)
    self.event.cvars['comps-excluded-packages'] = set(['passwd', 'setup'])

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core']
    self.excluded_pkgs = ['cpio', 'kudzu', 'passwd', 'setup']
    self.check_all(self.read_comps())

class Test_GroupsByRepo(_CompsEventTestCase):
  "comps generated, group included from specific repo"
  _conf = \
  """<comps>
    <group repoid="base">core</group>
    <group>base</group>
    <group repoid="base">printing</group>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base', 'printing']
    self.check_all(self.read_comps())

    # still need to check 'core' and 'printing' came from 'base' #!

class Test_MultipleGroupfiles(_CompsEventTestCase):
  "comps generated, multiple repositories with groupfiles"
  _conf = \
  """<comps>
    <group repoid="base">core</groups>
    <group>base-x</group>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base-x']
    self.check_all(self.read_comps())

    # still need to check that 'base-x' contains all packages listed in #!
    # both 'base' and 'livna' groupfiles in 'base-x' group #!

class Test_GroupDefaults(_CompsEventTestCase):
  # bug 106
  "comps generated, group defaults set appropriately"
  _conf = \
  """<comps>
    <group>base</group>
    <group default="true">web-server</group>
    <group default="false">printing</group>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    comps = self.read_comps()

    for group in ['web-server', 'printing']:
      self.failUnlessEqual(
        comps.get('/comps/group[id/text()="%s"]/default/text()' % group),
        self.event.config.get('group[text()="%s"]/@default' % group))

    # still need to test 'default' for both 'true' and 'false' #!

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('comps')

  suite.addTest(make_core_suite(CompsEventTestCase, distro, version, arch))
  suite.addTest(Test_Supplied(distro, version, arch))
  suite.addTest(Test_IncludePackages(distro, version, arch))
  suite.addTest(Test_IncludeCoreGroups(distro, version, arch))
  suite.addTest(Test_IncludeGroups(distro, version, arch))
  suite.addTest(Test_ExcludePackages(distro, version, arch))
  suite.addTest(Test_GroupsByRepo(distro, version, arch))
  ##suite.addTest(Test_MultipleGroupfiles(distro, version, arch))
  suite.addTest(Test_GroupDefaults(distro, version, arch))

  return suite
