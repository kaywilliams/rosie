#
# Copyright (c) 2013
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
from dtest      import EventTestCase, ModuleTestSuite
from dtest.core import make_extension_suite

class FilesTestCase(EventTestCase):
  moduleid = 'files'
  eventid  = 'files'
  _type = 'package'

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('files')

  suite.addTest(make_extension_suite(FilesTestCase, os, version, arch))

  return suite
