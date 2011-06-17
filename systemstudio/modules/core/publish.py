#
# Copyright (c) 2011
# Rendition Software, Inc. All rights reserved.
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

from systemstudio.util import pps

from systemstudio.errors    import SystemStudioError
from systemstudio.event     import Event
from systemstudio.sslogging   import L1

from systemstudio.modules.shared import DeployEventMixin
from systemstudio.modules.shared.publish import PublishEventMixin 

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PublishSetupEvent', 'PublishEvent' ],
  description = 'publish distribution to a web accessible location',
)

TYPE_DIR = pps.constants.TYPE_DIR
TYPE_NOT_DIR = pps.constants.TYPE_NOT_DIR

class PublishSetupEvent(PublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish-setup',
      parentid = 'setup',
      version = 1.00,
      provides = ['publish-content', 'publish-path', 'web-path'],
      suppress_run_message=True,
    )

    self.DATA = {
      'variables': ['distributionid'],
      'config': ['.'],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.localpath = self.get_local('local-dir', '/var/www/html/distributions')
    self.webpath   = self.get_remote('remote-url', 'distributions')

  def apply(self):
    self.cvars['publish-content'] = set()
    self.cvars['publish-path'] = self.localpath
    self.cvars['web-path'] = self.webpath 


class PublishEvent(PublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish',
      parentid = 'all',
      requires = ['web-path', 'publish-path', 'publish-content'],
      provides = ['published-distribution']
    )

    self.DATA =  {
      'variables': ['cvars[\'publish-path\']',
                    'cvars[\'publish-content\']',
                    'cvars[\'selinux-enabled\']'],
      'config':    ['.'],
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


class InterfaceIOError(SystemStudioError):
  message = ( "Error looking up information for interface '%(interface)s': "
              "%(message)s" )

class FQDNNotFoundError(SystemStudioError):
  message = ( "Unable to locate a fully-qualified domain name (FQDN) for "
              "IP address '%(ipaddr)s' on interface '%(interface)s'. "
              "Valid FQDNs must contain at least one '.' to separate host "
              "and domain parts. The hostname(s) found for this address "
              "include %(hostname)s. If this IP address is correct, please "
              "check with your network administrator to ensure the DNS reverse "
              "record is correctly configured. Otherwise, please specify an "
              "alternative interface for obtaining the IP address. See the "
              "SystemStudio documentation on 'Publish' for more information.") 
