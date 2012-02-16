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

from centosstudio.errors   import CentOSStudioError
from centosstudio.util     import pps 
from centosstudio.util     import rxml

from cstest       import (EventTestCase, ModuleTestSuite
                          _run_make)
from cstest.core  import make_core_suite


#------- Rpmbuild Classes -------#

class RpmbuildTestCase(EventTestCase):
  moduleid = 'rpmbuild'
  eventid  = 'rpmbuild'


#------- BuildMachine Classes -------#

class BuildMachineTestCase(EventTestCase):
  moduleid = 'rpmbuild'
  eventid  = 'build-machine'

  def __init__(self, distro, version, arch, conf=None):
    EventTestCase.__init__(self, distro, version, arch, conf=conf)
    self._add_config(
      """
      <rpmbuild>
      <definition>
        %s/../../share/centosstudio/examples/rpmbuild/rpmbuild-%s-%s.definition
      </definition>
      <srpm id='test'>
        <script></script>
      </srpm>
      </rpmbuild>
      """ % (pps.path(__file__).dirname.abspath(), version, arch))

  def setUp(self):
    EventTestCase.setUp(self)


#------- RPM Classes -------#

class TestRPMTestCase(EventTestCase):
  """
  The rpmbuild reads user config and generates classes at runtime. In our test
  case we provide config that causes a class to be generated, and then we test
  the functioning of that class
  """
  moduleid = 'rpmbuild'
  eventid  = 'test-rpm'

  _run_make(pps.path(__file__).dirname/'shared')

  def __init__(self, distro, version, arch, conf=None):
    EventTestCase.__init__(self, distro, version, arch, conf=conf)
    self._add_config(
      """
      <rpmbuild>
      <definition>
        %s/../../share/centosstudio/examples/rpmbuild/rpmbuild-%s-%s.definition
      </definition>
      <srpm id='package1'>
        <path>/tmp/buildrepos/SRPMS</path>
      </srpm>
      </rpmbuild>
      """ % (pps.path(__file__).dirname.abspath(), version, arch))

  def setUp(self):
    EventTestCase.setUp(self)



def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('rpmbuild')

  # rpmbuild cases
  suite.addTest(make_core_suite(RpmbuildTestCase, distro, version, arch))

  # build-machine and test-rpm test cases require libvirt
  try: 
    import libvirt
    suite.addTest(make_core_suite(BuildMachineTestCase, distro, version, arch))
    suite.addTest(make_core_suite(TestRPMTestCase, distro, version, arch))
  except ImportError:
    print "unable to import libvirt, skipping build-machine tests"

  return suite
