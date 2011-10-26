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
from centosstudio.sslogging import L1, L2, L3
from centosstudio.util      import pps

from centosstudio.modules.shared import RepomdMixin, DeployEventMixin
from centosstudio.modules.shared.config import ConfigEventMixin
from centosstudio.modules.shared.kickstart import KickstartEventMixin
from centosstudio.modules.shared.publish import PublishEventMixin

P = pps.path

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['TestInstallEvent'],
  description = 'performs test installations on a client system',
)

class TestInstallEvent(DeployEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-install',
      parentid = 'all',
      requires = ['test-webpath', ], 
    )

    self.DATA =  {
      'config':    [], # populated by mixin
      'input':     [], # ditto
      'output':    [], # ditto
      'variables': [], # populated in setup
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.webpath = self.cvars['test-webpath'] 
    self.kstext = self.cvars['test-kstext']
    self.repomdfile = self.cvars['test-repomdfile']
    self.DATA['variables'].extend(['webpath', 'kstext', 'repomdfile'])
    DeployEventMixin.setup(self)

  def run(self):
    self.install_triggers = [ 'install-script', 'kickstart', 'activate' ]
    DeployEventMixin.run(self)

  def apply(self):
    self.io.clean_eventcache()
