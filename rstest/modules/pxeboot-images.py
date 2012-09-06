#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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
from rstest      import EventTestCase, ModuleTestSuite
from rstest.core import make_core_suite

class PxebootImagesEventTestCase(EventTestCase):
  moduleid = 'pxeboot-images'
  eventid  = 'pxeboot-images'
  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbuild enabled='false'/>",
    "<config-rpm enabled='false'/>",
  ]

def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('pxeboot-images')

  suite.addTest(make_core_suite(PxebootImagesEventTestCase, distro, version, arch))

  return suite
