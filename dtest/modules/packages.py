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

from dtest      import EventTestCase, ModuleTestSuite, _run_make
from dtest.core import make_core_suite

from deploy.util import rxml
from deploy.util import pps 

from deploy.constants import KERNELS

REPODIR  = pps.path(__file__).dirname/'shared'

class PackagesEventTestCase(EventTestCase):
  moduleid = 'packages'
  eventid  = 'packages'
  _type = 'package'
  _conf = "<packages><package>kernel</package></packages>"

  def __init__(self, os, version, arch, conf=None):
    EventTestCase.__init__(self, os, version, arch, conf)
    self.included_groups = []
    self.included_pkgs = []
    self.excluded_pkgs = []

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

class Test_IncludePackages(PackagesEventTestCase):
  "packages included in user-required-packages"
  _conf = """<packages>
    <package>httpd</package>
  </packages>"""

  def __init__(self, os, version, arch, conf=None):
    PackagesEventTestCase.__init__(self, os, version, arch, conf=conf)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless('httpd' in self.event.cvars['user-required-packages'])

class Test_IncludeFile(PackagesEventTestCase):
  _conf = """<packages>
    <package dir='%s/repo1/RPMS/'>package1</package>
  </packages>""" % REPODIR

  _run_make(REPODIR)

  def __init__(self, os, version, arch, conf=None):
    PackagesEventTestCase.__init__(self, os, version, arch, conf=conf)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless('package1-1.0-2.noarch.rpm'
                    in [ x.basename for x in self.event.rpmsdir.listdir() ])


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('packages')

  suite.addTest(make_core_suite(PackagesEventTestCase, os, version, arch))
  suite.addTest(Test_IncludePackages(os, version, arch))
  suite.addTest(Test_IncludeFile(os, version, arch))

  return suite
