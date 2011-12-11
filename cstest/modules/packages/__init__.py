#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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

from cstest      import EventTestCase, ModuleTestSuite
from cstest.core import make_core_suite

class PackagesEventTestCase(EventTestCase):
  moduleid = 'packages'
  eventid  = 'packages'

def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('packages')

  suite.addTest(make_core_suite(PackagesEventTestCase, distro, version, arch))

  return suite
