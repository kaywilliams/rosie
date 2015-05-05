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
import os

from deploy.callback  import BuildDepsolveCallback
from deploy.event     import Event, CLASS_META
from deploy.dlogging import L1, L2, L3

from deploy.modules.shared import config
from deploy.modules.shared import DeployEventMixin
from deploy.modules.shared import KickstartEventMixin
from deploy.modules.shared import PublishSetupEventMixin
from deploy.modules.shared import MkrpmRpmBuildMixin

def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['BuildEvents', 'BuildSetupEvent', 'BuildKickstartEvent',
                   'BuildEvent'],
    description = 'creates remote machines',
  )

  return module_info

class BuildEvents(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'build-events',
      parentid = 'all',
      ptr = ptr,
      properties = CLASS_META,
      comes_after = ['autoclean'],
      suppress_run_message = True,
      )

class BuildSetupEvent(PublishSetupEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'build-setup',
      parentid = 'build-events',
      ptr = ptr,
      version = 1.0,
      requires = [],
      provides = ['build-setup'],
      suppress_run_message = True,
    ) 

    PublishSetupEventMixin.__init__(self)


class BuildKickstartEvent(KickstartEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'build-kickstart',
      parentid = 'build-events',
      ptr = ptr,
      version = 1.0,
      requires = ['build-setup'],
      provides = ['build-kickstart'],
      suppress_run_message = True,
    ) 

    KickstartEventMixin.__init__(self)

  def run(self):
    KickstartEventMixin.run(self)

    # publish kickstart file - note we are assuming the kickstart is the only
    # file in the pubdir
    pubdir = self.cvars['build-setup-options']['localpath']
    pubdir.rm(recursive=True, force=True)
    pubdir.mkdirs()
    self.copy(self.ksfile, pubdir, callback=self.link_callback)


class BuildEvent(DeployEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'build',
      parentid = 'build-events',
      ptr = ptr,
      requires = ['build-kickstart'], 
      conditionally_requires = [],
    )

    self.DATA =  {
      'config':    set(), # populated by mixin
      'input':     set(), # ditto
      'output':    set(), # ditto
      'variables': set(), # populated in setup
    }

    DeployEventMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    DeployEventMixin.setup(self)
