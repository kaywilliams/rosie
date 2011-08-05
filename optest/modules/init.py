#
# Copyright (c) 2011
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
from optest      import EventTestCase, ModuleTestSuite
from optest.core import make_core_suite

#------ init ------#
class InitEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'init'

#------ setup ------#
class SetupEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'setup'

#------ os ------#
class OSEventTestCase(EventTestCase):
  moduleid = 'init'
  eventid  = 'os'


def make_suite(distro, version, arch):
  suite = ModuleTestSuite('init')

  # init
  suite.addTest(make_core_suite(InitEventTestCase, distro, version, arch))

  # setup
  suite.addTest(make_core_suite(SetupEventTestCase, distro, version, arch))

  # os
  suite.addTest(make_core_suite(OSEventTestCase, distro, version, arch))

  return suite
