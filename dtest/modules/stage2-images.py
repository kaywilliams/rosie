#
# Copyright (c) 2015
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
from dtest        import EventTestCase, ModuleTestSuite
from dtest.core   import make_core_suite
from dtest.mixins import fdm_make_suite

class Stage2ImagesEventTestCase(EventTestCase):
  moduleid = 'stage2-images'
  eventid  = 'stage2-images'
  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbulid enabled='false'/>",
  ]

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('stage2-images')

  suite.addTest(make_core_suite(Stage2ImagesEventTestCase, os, version, arch))
  suite.addTest(fdm_make_suite(Stage2ImagesEventTestCase, os, version, arch))

  return suite
