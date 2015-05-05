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
from deploy.util import pps
from deploy.util import rxml

from dtest      import EventTestCase, ModuleTestSuite, _run_make
from dtest.core import make_core_suite


class RepomdEventTestCase(EventTestCase):
  moduleid = 'repomd'
  eventid  = 'repomd'
  _type = 'package'
  _conf = "<publish enabled='true'/>" # include release-rpm in repository


def make_suite(os, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname/'shared')

  suite = ModuleTestSuite('repomd')

  suite.addTest(make_core_suite(RepomdEventTestCase, os, version, arch))

  return suite
