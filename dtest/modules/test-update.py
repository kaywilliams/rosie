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
import unittest

from deploy.errors import DeployError
from deploy.util   import pps 
from deploy.util   import rxml 

from deploy.util.rxml import config 

from dtest      import EventTestCase, ModuleTestSuite
from dtest.core import make_extension_suite

from dtest.mixins import (psm_make_suite, PublishSetupMixinTestCase, 
                          DeployMixinTestCase, dm_make_suite)
from dtest.mixins import PackagesMixinTestCase, packages_mixin_make_suite


class TestUpdatePackagesEventTestCase(PackagesMixinTestCase, EventTestCase):
  moduleid = 'test-update'
  eventid  = 'test-update-packages'


class TestUpdateSetupEventTestCase(PublishSetupMixinTestCase, EventTestCase):
  moduleid = 'test-update'
  eventid  = 'test-update-setup'


class TestUpdateEventTestCase(DeployMixinTestCase, EventTestCase):
  moduleid = 'test-update'
  eventid  = 'test-update'


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('test-update')

  # packages
  # only running these in publish on an ongoing basis to decrease test time
  # suite.addTest(make_extension_suite(TestUpdatePackagesEventTestCase,
  #                                     os, version, arch))
  # suite.addTest(packages_mixin_make_suite(TestUpdatePackagesEventTestCase,
  #                                         os, version, arch))

  # setup
  suite.addTest(make_extension_suite(TestUpdateSetupEventTestCase, os, version, arch))

  # deploy
  suite.addTest(make_extension_suite(TestUpdateEventTestCase, os, version, 
                arch, offline=False))
  suite.addTest(dm_make_suite(TestUpdateEventTestCase, os, version, arch,))

  return suite
