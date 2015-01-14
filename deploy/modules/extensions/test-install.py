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
import os

from deploy.callback  import BuildDepsolveCallback
from deploy.event     import Event, CLASS_META
from deploy.dlogging import L1, L2, L3

from deploy.modules.shared import config
from deploy.modules.shared import DeployEventMixin
from deploy.modules.shared import PackagesEventMixin
from deploy.modules.shared import TestPublishEventMixin
from deploy.modules.shared import MkrpmRpmBuildMixin

def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['TestInstallPackagesEvent', 'TestInstallSetupEvent',
                   'TestInstallEvent'],
    description = 'performs test installations on client systems',
  )
  modname = __name__.split('.')[-1]
  new_rpm_events = config.make_config_rpm_events(ptr, modname, 'config-rpm', 
                                                 globals=globals())
  module_info['events'].extend(new_rpm_events)

  return module_info

class TestInstallPackagesEvent(PackagesEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'test-install-packages',
      parentid = 'setup-events',
      ptr = ptr,
      version = 1.00,
      conditionally_comes_before = ['packages'],
      suppress_run_message=True,
    )

    PackagesEventMixin.__init__(self)


class TestInstallSetupEvent(TestPublishEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'test-install-setup',
      parentid = 'test-events',
      conditionally_comes_after = ['test-update'],
      ptr = ptr,
      version = 1.0,
      requires = ['os-dir'],
    ) 

    TestPublishEventMixin.__init__(self)

class TestInstallEvent(DeployEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'test-install',
      parentid = 'test-events',
      ptr = ptr,
    )

    self.DATA =  {
      'config':    set(), # populated by mixin
      'input':     set(), # ditto
      'output':    set(), # ditto
      'variables': set(), # populated in setup
    }

    DeployEventMixin.__init__(self, reinstall=True, track_repomd=False)

  def setup(self):
    self.diff.setup(self.DATA)
    DeployEventMixin.setup(self)

  def run(self):
    DeployEventMixin.run(self)

