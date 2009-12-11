#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
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
from systembuildertest        import EventTestCase, ModuleTestSuite
from systembuildertest.core   import make_extension_suite
from systembuildertest.mixins import touch_input_files, remove_input_files

class KickstartEventTestCase(EventTestCase):
  moduleid = 'kickstart'
  eventid  = 'kickstart'
  _conf = [
    "<kickstart/>",
    "<rpmbuild enabled='false'/>",
  ]

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('kickstart')

  suite.addTest(make_extension_suite(KickstartEventTestCase, distro, version, arch))

  return suite
