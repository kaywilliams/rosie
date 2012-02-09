#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['TestUpdateSetupEvent', 'TestUpdateEvent'],
    description = 'performs test updates on client systems',
  )


class TestUpdateSetupEvent(TestPublishEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'test-update-setup',
      parentid = 'test-events',
      ptr = ptr,
      version = 1.0,
      requires = ['os-dir'],
      conditionally_requires = [ 'kickstart-file', 'rpmbuild-data'],
      # don't run if test-install event fails
      conditionally_comes_after = [ 'test-install' ],
      provides = ['test-update-repomdfile', 'test-update-kstext'],
    )

    TestPublishEventMixin.__init__(self)


class TestUpdateEvent(DeployEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'test-update',
      parentid = 'test-events',
      ptr = ptr,
      requires = ['test-update-repomdfile', 'test-update-kstext'], 
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
    self.kstext = self.cvars['test-update-kstext']
    self.repomdfile = self.cvars['test-update-repomdfile']
    self.DATA['variables'].extend(['kstext', 'repomdfile'])
    DeployEventMixin.setup(self)


