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

from centosstudio.util      import pps

from cstest        import EventTestCase, decorate
from cstest.core   import CoreTestSuite
from cstest.mixins import check_vm_config

__all__ = ['DeployMixinTestCase', 'dm_make_suite']

class DeployMixinTestCase(EventTestCase):
  def __init__(self, distro, version, arch, conf):
    self.hostname = 'test-%s-%s-%s.local' % (self.moduleid, version, arch)
    self._conf = [ 
      """
      <packages>
        <group>core</group>
        <group>base</group>
      </packages>
      """,
      """
      <%(module)s hostname='%(hostname)s' password='password'>
        <kickstart>
        <include xmlns='http://www.w3.org/2001/XInclude'
                 href='%(root)s/../../share/centosstudio/examples/ks.cfg'
                 parse='text'/>
        </kickstart>
        <include xmlns='http://www.w3.org/2001/XInclude'
                 href='%(root)s/../../share/centosstudio/examples/deploy.xml' 
                 xpointer="xpointer(/*/*[name()!='post-script'])"/>
      </%(module)s>
      """ % {'module'   : self.moduleid,
             'hostname' : self.hostname,
             'root'     : pps.path(__file__).dirname.abspath()}]
    EventTestCase.__init__(self, distro, version, arch, conf)

def DeployMixinTest_Teardown(self):
  self._testMethodDoc = "dummy test to teardown virtual machine"

  def post_tearDown():
    exec "import libvirt" in globals()

    # destroy and underfine vm
    conn = libvirt.open("qemu:///system")
    vm = conn.lookupByName(self.hostname)
    vm.destroy()
    vm.undefine()

    # delete vm image
    pool = conn.storagePoolLookupByName('default')
    vol = pool.storageVolLookupByName('%s.img' % self.hostname)
    vol.delete(0)

  decorate(self, 'tearDown', postfn=post_tearDown)
  
  return self

def dm_make_suite(TestCase, distro, version, arch, conf=None, xpath=None):
  suite = CoreTestSuite()
  suite.addTest(DeployMixinTest_Teardown(TestCase(distro, version, arch, conf)))
  return suite
