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
import array
import fcntl
import platform
import socket
import struct

from centosstudio.util import pps

from centosstudio.event     import Event
from centosstudio.cslogging   import L1

from centosstudio.modules.shared import DeployEventMixin
from centosstudio.modules.shared import KickstartEventMixin
from centosstudio.modules.shared import PublishSetupEventMixin 
from centosstudio.modules.shared import (ConfigRpmEvent,
                                         ConfigRpmEventMixin,
                                         make_rpm_events,
                                         MkrpmRpmBuildMixin,)

TYPE_DIR = pps.constants.TYPE_DIR
TYPE_NOT_DIR = pps.constants.TYPE_NOT_DIR

def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['PublishSetupEvent', 'KickstartEvent', 'PublishEvent', 
                   'DeployEvent'],
    description = 'publishes repository to a web accessible location',
  )
  modname = __name__.split('.')[-1]
  new_rpm_events = make_rpm_events(ptr, modname, 'rpm', globals=globals())
  module_info['events'].extend(new_rpm_events)

  return module_info

# -------- init method called by new_rpm_events -------- #
def __init__(self, ptr, *args, **kwargs):
  ConfigRpmEventMixin.__init__(self, ptr, *args, **kwargs)

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


class KickstartEvent(KickstartEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'kickstart',
      parentid = 'installer',
      ptr = ptr,
      version = 1.02,
      provides = ['kickstart-file', 'ks-path', 'initrd-image-content', 
                  'os-content'],
    )

    if self.config.getxpath('kickstart', False) is False: 
      self.disable()
      return

    self.DATA = {
      'config':    [],
      'variables': [],
      'output':    [],
    }

    KickstartEventMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    self.ksxpath = 'kickstart'
    KickstartEventMixin.setup(self)

  def run(self):
    KickstartEventMixin.run(self)

  def apply(self):
    self.cvars['kickstart-file'] = self.ksfile
    self.cvars['ks-path'] = pps.path('/%s' % self.cvars['kickstart-file'].basename)

  def verify_cvars(self):
    "kickstart file exists"
    self.verifier.failUnlessExists(self.cvars['kickstart-file'])


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
      conditionally_requires = ['repomd-file'],
      requires = ['published-repository'],
    )

    self.DATA =  {
      'variables': [],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

    DeployEventMixin.__init__(self)
    if self.scripts_provided is False: self.disable()

  def setup(self):
    self.diff.setup(self.DATA)

    self.webpath = self.cvars['publish-setup-options']['webpath'] 
    # allowing deploy event to run when the repocreate is disabled for 
    # improved testing performance
    if 'repomd-file' in self.cvars:
      self.repomdfile = self.cvars['repomd-file']
    else:
      self.repomdfile = ''
    # not setting kstext since kickstart is not a trigger for this event

    self.DATA['variables'].extend(['webpath', 'repomdfile'])
    DeployEventMixin.setup(self)

  def run(self):
    DeployEventMixin.run(self)
