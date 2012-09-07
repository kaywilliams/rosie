#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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

from repostudio.callback  import BuildDepsolveCallback
from repostudio.event     import Event, CLASS_META
from repostudio.cslogging import L1, L2, L3
from repostudio.util      import pps

from repostudio.modules.shared import config
from repostudio.modules.shared import DeployEventMixin
from repostudio.modules.shared import TestPublishEventMixin
from repostudio.modules.shared import MkrpmRpmBuildMixin

P = pps.path

def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['TestUpdateSetupEvent', 'TestUpdateEvent'],
    description = 'performs test updates on client systems',
  )
  modname = __name__.split('.')[-1]
  new_rpm_events = config.make_config_rpm_events(ptr, modname, 'config-rpm', 
                                                 globals=globals())
  module_info['events'].extend(new_rpm_events)

  return module_info


class TestUpdateSetupEvent(TestPublishEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'test-update-setup',
      parentid = 'test-events',
      ptr = ptr,
      version = 1.0,
      requires = ['os-dir'],
      conditionally_requires = [ 'kickstart-file'],
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
    self.DATA['variables'].append('repomdfile')
    self.default_install_triggers = [ 'kickstart', 'install_scripts',
                                      'post_install_scripts' ]
    DeployEventMixin.setup(self)

