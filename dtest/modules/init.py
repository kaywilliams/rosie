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
from dtest.core import make_core_suite

#------ init ------#
class InitEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'init'
  _mode = 'package'

#------ setup ------#
class SetupEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'setup-events'
  _mode = 'package'

#------ os ------#
class OSEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'os-events'
  _mode = 'package'


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('init')

  # init
  suite.addTest(make_core_suite(InitEventTestCase, os, version, arch))

  # setup
  suite.addTest(make_core_suite(SetupEventTestCase, os, version, arch))

  # os
  suite.addTest(make_core_suite(OSEventTestCase, os, version, arch))

  return suite
