#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
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

from centosstudio.errors import CentOSStudioError
from centosstudio.util   import pps 
from centosstudio.util   import rxml 

from centosstudio.util.rxml import datfile

from cstest      import EventTestCase, ModuleTestSuite, TestBuild
from cstest.core import make_extension_suite

from cstest.mixins import (psm_make_suite, DeployMixinTestCase,
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

  def __init__(self, distro, version, arch, *args, **kwargs):
    PublishSetupEventTestCase.__init__(self, distro, version, arch, *args, **kwargs)

  def setUp(self):
    PublishSetupEventTestCase.setUp(self)

    if not self.event: # module disabled
      return

    # set password and crypt password in datfile
    root = self.event.parse_datfile()
    mod = root.getxpath('%s' % self.moduleid, '')
    if len(mod) == 0:
      mod = datfile.uElement('%s' % self.moduleid, parent=root)
    datfile.uElement('crypt-password', text='$6$OJZ6KCfu$GcpaU07JTXN1y/bMSunZJDt.BBMOl1gs7ZoJy1c6No4iJyyXUFhD3X2ar1ZT2qKN/NS9KLDoyczmuIfVyDPiZ/', parent=mod)
    root.write()

  def tearDown(self):
    EventTestCase.tearDown(self) 


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('test-update')

  # setup
  suite.addTest(make_extension_suite(PublishSetupEventTestCase, distro, version, arch))

  # deploy
  suite.addTest(make_extension_suite(TestUpdateEventTestCase, distro, version, arch))

  return suite
