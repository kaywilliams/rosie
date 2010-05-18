#
# Copyright (c) 2010
# Solution Studio Foundation. All rights reserved.
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
from sstest      import EventTestCase, ModuleTestSuite
from sstest.core import make_core_suite

class BuildstampEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'buildstamp'
  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbuild enabled='false'/>",
  ]

class DiscinfoEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'discinfo'
  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbuild enabled='false'/>",
  ]

class TreeinfoEventTestCase(EventTestCase):
  moduleid = 'infofiles'
  eventid  = 'treeinfo'
  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbuild enabled='false'/>",
  ]

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('infofiles')

  # buildstamp
  suite.addTest(make_core_suite(BuildstampEventTestCase, distro, version, arch))

  # discinfo
  suite.addTest(make_core_suite(DiscinfoEventTestCase, distro, version, arch))

  # treeinfo
  suite.addTest(make_core_suite(TreeinfoEventTestCase, distro, version, arch))

  return suite
