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
import re
import unittest

from lxml import etree

from deploy.util      import pps
from deploy.util      import rxml

from dtest        import EventTestCase, decorate
from dtest.core   import CoreTestSuite
from dtest.mixins import check_vm_config

__all__ = ['DeployMixinTestCase', 'dm_make_suite']

class DeployMixinTestCase:
  _type = 'system'
  
  def __init__(self, os, version, arch, module=None):
    self.mod = module or self.moduleid
    EventTestCase.__init__(self, os, version, arch)

    # get default deploy config
    deploy = rxml.config.parse(
      '%s/../../share/deploy/templates/virt-deploy.xml' %  
      pps.path(__file__).dirname.abspath()).getroot()

    # update default virt-install image size
    install = deploy.getxpath("/*/script[@id='virt-install']")
    text = install.getxpath("text()")
    # bad, could relace size arguments in options other than '--disk'
    install.text = re.sub('size=[0-9]*', 'size=6', text)

    # update packages
    pkgcontent=etree.XML("""
    <packages>
      <group>core</group>
      <!--add NM as a workaround RTNETLINK/NOZEROCONF issue in el5-->
      <package>NetworkManager</package>
    </packages>""")
    packages = self.conf.getxpath('/*/packages', None)
    if packages is None:
      packages = rxml.config.Element('packages', parent=self.conf)
    packages.extend(pkgcontent.xpath('/*/*'))

    # update module
    self.hostname = "dtest-%s-%s-%s" % (self.moduleid, self.version,
                                        self.arch.replace("_", "-"))
    self.domain = '.local'

    mod = self.conf.getxpath('/*/%s' % self.mod, None)
    if mod is None:
      mod = rxml.config.Element('%s' % self.mod, parent=self.conf)
    rxml.config.Element('hostname', parent=mod, text=self.hostname)
    rxml.config.Element('password', parent=mod, text='password')

    if self.mod != 'test-install':
      triggers = rxml.config.Element('triggers', parent=mod)
      triggers.text = 'kickstart install_scripts'

    mod.extend(deploy.xpath("/*/*[name()!='script']"))
    mod.extend(deploy.xpath("/*/script[@id!='post']"))
  

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
    vm = conn.lookupByName(self.hostname + self.domain)
    vm.destroy()

  self.setUp = setUp
  self.runTest = runTest
  self.tearDown = tearDown
  decorate(self, 'tearDown', postfn=post_tearDown)
  
  return self

def dm_make_suite(TestCase, os, version, arch):
  suite = CoreTestSuite()
  suite.addTest(DeployMixinTest_Teardown(TestCase(os, version, arch)))
  return suite
