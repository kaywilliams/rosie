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

from lxml import etree

from centosstudio.util      import pps
from centosstudio.util      import rxml

from cstest        import EventTestCase, decorate
from cstest.core   import CoreTestSuite
from cstest.mixins import check_vm_config

__all__ = ['DeployMixinTestCase', 'dm_make_suite']

class DeployMixinTestCase:
  def __init__(self, distro, version, arch, module=None):
    self.mod = module or self.moduleid
    EventTestCase.__init__(self, distro, version, arch)
    deploy = rxml.config.parse(
      '%s/../../share/centosstudio/examples/common/deploy.xml' %  
      pps.path(__file__).dirname.abspath()).getroot()

    # update packages
    pkgcontent=etree.XML("""
    <packages>
      <group>core</group>
      <group>base</group>
    </packages>""")
    packages = self.conf.get('/*/packages', None)
    if packages is None:
      packages = rxml.config.Element('packages', parent=self.conf)
    packages.extend(pkgcontent.xpath('/*/*'))

    # update config-rpm
    config_rpm = self.conf.get('/*/config-rpm', None)
    if config_rpm is None:
      config_rpm = rxml.config.Element('config-rpm', parent=self.conf)
    config_rpm.extend(deploy.xpath('/*/config-rpm/*'))

    # update module
    self.hostname = "cstest-%s-%s-%s.local" % (self.moduleid, self.version,
                                               self.arch) 
    mod = self.conf.get('/*/%s' % self.mod, None)
    if mod is None:
      mod = rxml.config.Element('%s' % self.mod, parent=self.conf)
    mod.set('hostname', self.hostname)
    mod.set('password', 'password')

    trigger = mod.get('trigger', None)
    if trigger is None:
      trigger = rxml.config.Element('trigger', parent=mod)
      if self.mod != 'test-install':
        trigger.set('triggers', 'kickstart, install-scripts')
      trigger.extend(deploy.xpath('/*/trigger/*'))

    mod.extend(deploy.xpath(("/*/*[name()!='post' and "
                                  "name()!='trigger' and "
                                  "name()!='config-rpm']")))

  def runTest(self):
    self.tb.dispatch.execute(until='deploy')


def DeployMixinTest_Teardown(self):
  self._testMethodDoc = "dummy test to shutoff virtual machine"
  def setUp(): 
    EventTestCase.setUp(self)

  def runTest():
    pass

  def tearDown():
    EventTestCase.tearDown(self) 

  def post_tearDown():
    exec "import libvirt" in globals()

    # shutdown vm
    conn = libvirt.open("qemu:///system")
    vm = conn.lookupByName(self.hostname)
    vm.destroy()

  self.setUp = setUp
  self.runTest = runTest
  self.tearDown = tearDown
  decorate(self, 'tearDown', postfn=post_tearDown)
  
  return self

def dm_make_suite(TestCase, distro, version, arch):
  suite = CoreTestSuite()
  suite.addTest(DeployMixinTest_Teardown(TestCase(distro, version, arch)))
  return suite
