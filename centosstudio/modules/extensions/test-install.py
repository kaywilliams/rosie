#
# Copyright (c) 2011
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
import os

from centosstudio.callback  import BuildDepsolveCallback
from centosstudio.event     import Event, CLASS_META
from centosstudio.cslogging import L1, L2, L3
from centosstudio.util      import pps

from centosstudio.modules.shared import DeployEventMixin
from centosstudio.modules.shared.testpublish import TestPublishEventMixin

P = pps.path

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['TestInstallPublishEvent', 'TestInstallEvent'],
  description = 'performs test installations on client systems',
)

class TestInstallPublishEvent(TestPublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-install-publish',
      parentid = 'test-events',
      version = 1.0,
      requires = ['os-dir'],
      conditionally_requires = [ 'kickstart-file', 'config-release'],
      provides = ['test-install-webpath', 'test-install-repomdfile', 
                  'test-install-kstext'],
    ) 

    self.localpath = self.get_local('/var/www/html/solutions/test-install')
    self.webpath = self.get_remote('solutions/test-install')

    TestPublishEventMixin.__init__(self)


class TestInstallEvent(DeployEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-install',
      parentid = 'test-events',
      requires = ['test-install-webpath', 'test-install-kstext', 
                  'treeinfo-text'], 
      conditionally_requires = [ 'test-install-repomdfile', 'config-release'],
    )

    DeployEventMixin.__init__(self)

    self.DATA =  {
      'config':    [], # populated by mixin
      'input':     [], # ditto
      'output':    [], # ditto
      'variables': [], # populated in setup
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.webpath = self.cvars['test-install-webpath'] 
    self.kstext = self.cvars['test-install-kstext']
    self.titext = self.cvars['treeinfo-text']
    self.repomdfile = self.cvars['test-install-repomdfile']
    if 'config-release' in self.cvars:
      self.config_release = self.cvars['config-release']
    else:
      self.config_release = None
    self.DATA['variables'].extend(['webpath', 'kstext', 'titext', 
                                   'repomdfile', 'config_release'])
    DeployEventMixin.setup(self)

  def run(self):
    self.install_triggers = [ 'install-script', 'kickstart', 'treeinfo',
                              'config-release', 'activate' ]
    DeployEventMixin.run(self)

