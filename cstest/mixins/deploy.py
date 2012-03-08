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
  pass

def DeployMixinTest_Teardown(self):
  self._testMethodDoc = "dummy test to shutoff virtual machine"

  def setUp(): 
    EventTestCase.setUp(self)

  def tearDown():
    EventTestCase.tearDown(self) 

  def post_tearDown():
    exec "import libvirt" in globals()

    # shutdown vm
    conn = libvirt.open("qemu:///system")
    vm = conn.lookupByName(self.hostname)
    vm.destroy()

  self.setUp = setUp
  self.tearDown = tearDown
  decorate(self, 'tearDown', postfn=post_tearDown)
  
  return self

def dm_make_suite(TestCase, distro, version, arch):
  suite = CoreTestSuite()
  suite.addTest(DeployMixinTest_Teardown(TestCase(distro, version, arch)))
  return suite
