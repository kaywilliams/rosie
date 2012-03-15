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

class DeployMixinTestCase:
  _conf = [
    """
    <packages>
      <group>core</group>
      <group>base</group>
    </packages>
    """,
    """
    <publish password='password'>
     <trigger-script triggers='kickstart, install-script'>
      <include 
        xmlns='http://www.w3.org/2001/XInclude'
        href='%(root)s/../../share/centosstudio/examples/common/deploy.xml' 
        xpointer="xpointer(/*/trigger-script/text())]"/>
      </trigger-script>

      <kickstart>
      <include 
         xmlns='http://www.w3.org/2001/XInclude'
         href='%(root)s/../../share/centosstudio/examples/common/ks.cfg'
         parse='text'/>
      </kickstart>

      <include 
        xmlns='http://www.w3.org/2001/XInclude'
        href='%(root)s/../../share/centosstudio/examples/common/deploy.xml' 
        xpointer="xpointer(/*/*[name()!='post-script' and
                                name()!='trigger-script'])"/>
    </publish>
    """ % {'root' : pps.path(__file__).dirname.abspath()}]

  def __init__(self, distro, version, arch):
    EventTestCase.__init__(self, distro, version, arch)
    self.hostname = "cstest-%s-%s-%s.local" % (self.moduleid, self.version, 
                                          self.arch)
    self.conf.get("/*/publish").set('hostname', self.hostname)

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
