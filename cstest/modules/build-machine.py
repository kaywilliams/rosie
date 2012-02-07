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
from centosstudio.util     import rxml

from cstest       import EventTestCase, ModuleTestSuite
from cstest.core  import make_core_suite


class BuildMachineTestCase(EventTestCase):
  moduleid = 'build-machine'
  eventid  = 'build-machine'

  def setUp(self):
    # add type element to main
    main = self.conf.get('/*/main')
    main.append(rxml.config.Element('type', text='component'))

    # add definition element to rpmbuild
    rpmbuild = self.conf.get('/*/rpmbuild')
    rpmbuild.append(rxml.config.Element('definition', 
      text='%s/../../share/centosstudio/examples/rpmbuild/'
           'rpmbuild-%s-%s.definition' % 
      (pps.path(__file__).dirname.abspath(), self.version, self.arch)))

    EventTestCase.setUp(self)


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('build-machine')

  # skip tests on non-libvirt machines
  try:
    import libvirt
  except:
    print "unable to import libvirt, skipping build-machine tests"
    return suite

  # else add tests
  suite.addTest(make_core_suite(BuildMachineTestCase, distro, version, arch))
  return suite
