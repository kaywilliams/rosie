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

from dtest      import EventTestCase, ModuleTestSuite, TestBuild
from dtest.core import make_extension_suite

from dtest.mixins import (psm_make_suite, DeployMixinTestCase,
                           dm_make_suite, check_vm_config)


class PublishSetupEventTestCase(DeployMixinTestCase, EventTestCase):
  moduleid = 'test-update'
  eventid  = 'test-update-setup'

  def tearDown(self):
    # 'register' publish_path for deletion upon test completion
    self.output.append(
        self.event.cvars['%s-setup-options' % self.moduleid]['localpath'])
    EventTestCase.tearDown(self)


class TestUpdateEventTestCase(PublishSetupEventTestCase):
  moduleid = 'test-update'
  eventid  = 'test-update'

  def __init__(self, os, version, arch, *args, **kwargs):
    PublishSetupEventTestCase.__init__(self, os, version, arch, *args, **kwargs)

  def setUp(self):
    PublishSetupEventTestCase.setUp(self)

    if not self.event: # module disabled
      return

    # set password and crypt password in datfile
    root = self.event.parse_datfile()
    mod = root.getxpath('%s' % self.moduleid, '')
    if len(mod) == 0:
      mod = config.uElement('%s' % self.moduleid, parent=root)
    config.uElement('crypt-password', text='$6$OJZ6KCfu$GcpaU07JTXN1y/bMSunZJDt.BBMOl1gs7ZoJy1c6No4iJyyXUFhD3X2ar1ZT2qKN/NS9KLDoyczmuIfVyDPiZ/', parent=mod)
    self.event.write_datfile(root)

  def tearDown(self):
    EventTestCase.tearDown(self) 


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('test-update')

  # setup
  suite.addTest(make_extension_suite(PublishSetupEventTestCase, os, version, arch))

  # deploy
  if check_vm_config():
    suite.addTest(make_extension_suite(TestUpdateEventTestCase, os, version, arch))

  return suite
