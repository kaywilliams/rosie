#
# Copyright (c) 2012
# CentOS Solutions Foundation. All rights reserved.
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
from centosstudio.modules.shared import TestPublishEventMixin

P = pps.path

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['TestInstallSetupEvent', 'TestInstallEvent'],
  description = 'performs test installations on client systems',
)


class TestInstallSetupEvent(TestPublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-install-setup',
      parentid = 'test-events',
      version = 1.0,
      requires = ['os-dir'],
      conditionally_requires = [ 'kickstart-file', 'rpmbuild-data'],
      provides = [ 'test-install-repomdfile', 'test-install-kstext'],
    ) 

    TestPublishEventMixin.__init__(self)


class TestInstallEvent(DeployEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-install',
      parentid = 'test-events',
      requires = [ 'test-install-kstext', 'treeinfo-text'], 
      conditionally_requires = [ 'test-install-repomdfile', 'rpmbuild-data'],
    )

    self.DATA =  {
      'config':    [], # populated by mixin
      'input':     [], # ditto
      'output':    [], # ditto
      'variables': [], # populated in setup
    }

    DeployEventMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.kstext = self.cvars['test-install-kstext']
    self.titext = self.cvars['treeinfo-text']
    self.repomdfile = self.cvars['test-install-repomdfile']
    for r in ['release-rpm', 'config-rpm']:
      try:
        setattr(self, '%s_release' % r.replace('-', '_'), 
                self.cvars['rpmbuild-data'][r]['rpm-release'])
      except KeyError:
        setattr(self, '%s_release' % r.replace('-', '_'), None)
    self.DATA['variables'].extend([ 'kstext', 'titext', 'release_rpm_release',
                                    'config_rpm_release'])
    DeployEventMixin.setup(self)

  def run(self):
    self.install_triggers = [ 'install-scripts', 'kickstart', 'treeinfo',
                              'release-rpm-release', 'config-rpm-release' ]
    DeployEventMixin.run(self)

