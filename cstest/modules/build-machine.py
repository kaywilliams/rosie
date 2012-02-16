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
from centosstudio.util     import pps 

from cstest       import EventTestCase, ModuleTestSuite
from cstest.core  import make_core_suite


class BuildMachineTestCase(EventTestCase):
  moduleid = 'build-machine'
  eventid  = 'build-machine'

  def __init__(self, distro, version, arch, conf=None):
    EventTestCase.__init__(self, distro, version, arch, conf=conf)
    sections = [
      """
      <build-machine>
      <definition>
        %s/../../share/centosstudio/examples/rpmbuild/rpmbuild-%s-%s.definition
      </definition>
      </build-machine>
      """ % (pps.path(__file__).dirname.abspath(), version, arch),
      """
      <srpmbuild>
      <srpm id='test'>
        <script></script>
      </srpm>
      </srpmbuild>
      """ ]
    for section in sections:
      self._add_config(section)

  def setUp(self):
    EventTestCase.setUp(self)


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('build-machine')

  # build-machine test cases require libvirt
  try: 
    import libvirt
    suite.addTest(make_core_suite(BuildMachineTestCase, distro, version, arch))
  except ImportError:
    print "unable to import libvirt, skipping build-machine tests"

  return suite
