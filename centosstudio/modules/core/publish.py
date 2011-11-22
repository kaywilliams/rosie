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
import array
import fcntl
import platform
import socket
import struct

from centosstudio.util import pps

from centosstudio.errors    import CentOSStudioError
from centosstudio.event     import Event
from centosstudio.cslogging   import L1

from centosstudio.modules.shared import DeployEventMixin
from centosstudio.modules.shared.kickstart import KickstartEventMixin
from centosstudio.modules.shared.publish import PublishEventMixin 

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PublishSetupEvent', 'KickstartEvent', 'PublishEvent', 
                 'DeployEvent'],
  description = 'publishes solution to a web accessible location',
)

TYPE_DIR = pps.constants.TYPE_DIR
TYPE_NOT_DIR = pps.constants.TYPE_NOT_DIR

class PublishSetupEvent(PublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish-setup',
      parentid = 'setup-events',
      version = 1.00,
      provides = ['publish-content', 'publish-path', 'web-path'],
      suppress_run_message=True,
    )

    self.DATA = {
      'variables': ['solutionid'],
      'config': ['local-dir', 'remote-url'],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.localpath = self.get_local('/var/www/html/solutions')
    self.webpath   = self.get_remote('solutions')

  def apply(self):
    self.cvars['publish-content'] = set()
    self.cvars['publish-path'] = self.localpath
    self.cvars['web-path'] = self.webpath 


class KickstartEvent(KickstartEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'kickstart',
      parentid = 'installer',
      version = 1.02,
      provides = ['kickstart-file', 'ks-path', 'initrd-image-content', 
                  'os-content'],
    )

    KickstartEventMixin.__init__(self)

    self.DATA = {
      'config':    ['kickstart'],
      'variables': ['kickstart_mixin_version'],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.kickstart_provided = self.config.get('kickstart', False)
    if self.kickstart_provided is False: return

    self.ksxpath = 'kickstart'
    KickstartEventMixin.setup(self)

  def check(self):
    if self.kickstart_provided is False: 
      return False
    else:
      return self.diff.test_diffs()

  def run(self):
    KickstartEventMixin.run(self)

  def apply(self):
    if self.kickstart_provided is False: return

    self.cvars['kickstart-file'] = self.ksfile
    self.cvars['ks-path'] = pps.path('/%s' % self.cvars['kickstart-file'].basename)

  def verify_cvars(self):
    "kickstart file exists"

    if self.kickstart_provided is False: return
    self.verifier.failUnlessExists(self.cvars['kickstart-file'])


class PublishEvent(PublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish',
      parentid = 'publish-events',
      requires = ['publish-path', 'publish-content'],
      provides = ['published-repository']
    )

    self.DATA =  {
      'variables': ['cvars[\'publish-path\']',
                    'cvars[\'publish-content\']',
                    'cvars[\'selinux-enabled\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.add_fpaths(self.cvars['publish-content'], self.cvars['publish-path'])

  def clean(self):
    Event.clean(self)
    self.cvars['publish-path'].rm(recursive=True, force=True)

  def run(self):
    "Publish the contents of SOFTWARE_STORE to PUBLISH_STORE"
    self.io.process_files(text="publishing to '%s'" % self.cvars['publish-path'],
                       callback=Event.link_callback)
    self.chcon(self.cvars['publish-path'])

  def apply(self):
    self.io.clean_eventcache()

    expected = set(self.diff.output.oldoutput.keys())
    existing = set(self.cvars['publish-path'].findpaths(
                 mindepth=1, type=TYPE_NOT_DIR))
    # delete files in publish path no longer needed
    for path in existing.difference(expected):
      path.rm()
    # delete empty directories in publish path
    for dir in [ d for d in
                 self.cvars['publish-path'].findpaths(mindepth=1, type=TYPE_DIR)
                 if not d.listdir(all=True) ]:
      dir.removedirs()


class DeployEvent(DeployEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'deploy',
      parentid = 'publish-events',
      requires = ['web-path', 'repomd-file', 'published-repository'],
    )

    self.DATA =  {
      'variables': [],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    if self.scripts_provided is False: return

    self.webpath = self.cvars['web-path'] / 'os'
    self.repomdfile = self.cvars['repomd-file']
    # not setting kstext since kickstart is not a trigger for this event

    self.DATA['variables'].extend(['webpath', 'repomdfile'])
    DeployEventMixin.setup(self)

  def check(self):
    if self.scripts_provided is False: 
      return False
    else:
      return self.diff.test_diffs()

  def run(self):
    DeployEventMixin.run(self)

  def apply(self):
    self.io.clean_eventcache()


##### Error Classes #####

class InterfaceIOError(CentOSStudioError):
  message = ( "Error looking up information for interface '%(interface)s': "
              "%(message)s" )

class FQDNNotFoundError(CentOSStudioError):
  message = ( "Unable to locate a fully-qualified domain name (FQDN) for "
              "IP address '%(ipaddr)s' on interface '%(interface)s'. "
              "Valid FQDNs must contain at least one '.' to separate host "
              "and domain parts. The hostname(s) found for this address "
              "include %(hostname)s. If this IP address is correct, please "
              "check with your network administrator to ensure the DNS reverse "
              "record is correctly configured. Otherwise, please specify an "
              "alternative interface for obtaining the IP address. See the "
              "CentOS Studio documentation on 'Publish' for more information.") 
