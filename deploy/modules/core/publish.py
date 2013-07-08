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
from deploy.util import pps

from deploy.event     import Event
from deploy.dlogging  import L1

from deploy.modules.shared import config
from deploy.modules.shared import DeployEventMixin
from deploy.modules.shared import KickstartEventMixin
from deploy.modules.shared import PublishSetupEventMixin 
from deploy.modules.shared import ReleaseRpmEventMixin
from deploy.modules.shared import MkrpmRpmBuildMixin 

TYPE_DIR = pps.constants.TYPE_DIR
TYPE_NOT_DIR = pps.constants.TYPE_NOT_DIR

def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['PublishSetupEvent', 'ReleaseRpmEvent', 'KickstartEvent',
                   'PublishEvent', 'DeployEvent'],
    description = 'publishes repository to a web accessible location',
  )
  modname = __name__.split('.')[-1]
  new_rpm_events = config.make_config_rpm_events(ptr, modname, 'config-rpm', 
                                                 globals=globals())
  module_info['events'].extend(new_rpm_events)

  return module_info


class PublishSetupEvent(PublishSetupEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'publish-setup',
      parentid = 'setup-events',
      ptr = ptr,
      version = 1.00,
      provides = ['publish-content' ],
      suppress_run_message=True,
    )

    self.DATA = {
      'variables': [],
      'config': [],
    }

    PublishSetupEventMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    PublishSetupEventMixin.setup(self)

  def apply(self):
    self.cvars['publish-content'] = set()


class ReleaseRpmEvent(ReleaseRpmEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'release-rpm',
      parentid = 'rpmbuild',
      ptr = ptr,
      version = '1.00',
      provides = ['os-content', 'release-rpm',
                  'gpgcheck-enabled', 'gpgkeys', 'gpgkey-ids'],
      requires = ['publish-setup-options'],
      conditionally_comes_before = ['config-rpms'],
    )

    self.DATA = {
      'variables': [],
      'config':    [], # set by ReleaseRpmEventMixin
      'input':     [],
      'output':    [],
    }

    ReleaseRpmEventMixin.__init__(self) 

  def setup(self):
    ReleaseRpmEventMixin.setup(self, 
      webpath=self.cvars['publish-setup-options']['webpath'])

  def run(self):
    ReleaseRpmEventMixin.run(self)

  def apply(self):
    ReleaseRpmEventMixin.apply(self)
    self.cvars['release-rpm'] = self.rpminfo['name']


class KickstartEvent(KickstartEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'kickstart',
      parentid = 'installer',
      ptr = ptr,
      version = 1.02,
      provides = ['initrd-image-content', 'os-content'],
    )

    if self.config.getxpath('kickstart', False) is False: 
      self.disable()
      return

    KickstartEventMixin.__init__(self)


class PublishEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'publish',
      parentid = 'publish-events',
      ptr = ptr,
      conditionally_comes_after = ['test-events'],
      requires = ['publish-content', 'publish-setup-options'],
      provides = ['published-repository']
    )

    self.DATA =  {
      'variables': ['cvars[\'publish-setup-options\'][\'localpath\']',
                    'cvars[\'publish-content\']',
                    'cvars[\'selinux-enabled\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.add_fpaths(self.cvars['publish-content'], 
                       self.cvars['publish-setup-options']['localpath'])

  def clean(self):
    Event.clean(self)
    self.cvars['publish-setup-options']['localpath'].rm(
                                        recursive=True, force=True)

  def run(self):
    "Publish the repository"
    self.io.process_files(text="publishing to '%s'" % 
                          self.cvars['publish-setup-options']['localpath'],
                       callback=self.link_callback)
    self.io.chcon(self.cvars['publish-setup-options']['localpath'])
 
  def clean_eventcache(self):
    # custom clean_eventcache method to deal with files outside the metadata
    # folder
    self.io.clean_eventcache()
    expected = set(self.diff.output.oldoutput.keys())
    existing = set(self.cvars['publish-setup-options']['localpath'].findpaths(
                 mindepth=1, type=TYPE_NOT_DIR))
    # delete files in publish path no longer needed
    for path in existing.difference(expected):
      path.rm()
    # delete empty directories in publish path
    for dir in [ d for d in
                 self.cvars['publish-setup-options']['localpath'].findpaths(
                 mindepth=1, type=TYPE_DIR)
                 if not d.listdir(all=True) ]:
      dir.removedirs()


class DeployEvent(DeployEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'deploy',
      parentid = 'publish-events',
      ptr = ptr,
      requires = ['publish-setup-options'],
      conditionally_requires = ['published-repository'],
    )

    self.DATA =  {
      'variables': [],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

    DeployEventMixin.__init__(self)
    if not self.config.xpath('script', []): self.disable()

  def setup(self):
    self.diff.setup(self.DATA)
    DeployEventMixin.setup(self)
