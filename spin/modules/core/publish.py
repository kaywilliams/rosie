#
# Copyright (c) 2007, 2008
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
import fcntl
import socket
import struct

from rendition import pps
from rendition import shlib

from spin.constants import *
from spin.event     import Event
from spin.logging   import L1

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PublishSetupEvent', 'PublishEvent'],
  description = 'links distribution output to a publish location',
)

TYPE_DIR = pps.constants.TYPE_DIR
TYPE_NOT_DIR = pps.constants.TYPE_NOT_DIR

class PublishSetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish-setup',
      parentid = 'setup',
      provides = ['publish-content', 'publish-path', 'web-path'],
      suppress_run_message=True,
    )

    self.DATA = {
      'variables': ['distroid'],
      'config': ['.'],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    prefix = \
      pps.path(self.config.get('path-prefix/text()', 'distros')) / self.distroid
    self.web_path = \
      pps.path(self.config.get('remote-webroot/text()',
                               'http://' + self._get_host())) / prefix
    self.publish_path = \
      pps.path(self.config.get('local-webroot/text()', '/var/www/html')) / prefix

  def apply(self):
    self.cvars['publish-content'] = set()
    self.cvars['publish-path'] = self.publish_path
    self.cvars['web-path'] = self.web_path

  def _get_host(self, ifname='eth0'):
    if self.config.get('remote-webroot/@use-hostname', 'False') in BOOLEANS_TRUE:
      return socket.gethostname()
    else:
      # TODO - improve this, it's not particularly accurate in some cases
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                          0x8915,
                                          struct.pack('256s', ifname[:15]))[20:24])


class PublishEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish',
      parentid = 'all',
      requires = ['publish-path', 'publish-content'],
    )

    self.DATA =  {
      'variables': ['cvars[\'publish-path\']',
                    'cvars[\'publish-content\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.add_fpaths(self.cvars['publish-content'], self.cvars['publish-path'])

  # overriding Event method to remove publish-path which is outside the mddir
  # this is a hack, better would be to generalize clean_eventcache
  # to clean all event output, not just output in the metadata dir
  def clean(self):
    Event.clean(self)
    self.cvars['publish-path'].rm(recursive=True, force=True)

  def run(self):
    "Publish the contents of SOFTWARE_STORE to PUBLISH_STORE"
    self.log(1, L1("publishing to '%s'" % self.cvars['publish-path']))

    # using link w/strict rather than io.sync to remove files outside the mddir
    self.cvars['publish-path'].mkdirs()
    for path in self.cvars['publish-content']:
      self.link(path, self.cvars['publish-path'], strict=True)

    if self.cvars['selinux-enabled']:
      shlib.execute('chcon -R --type=httpd_sys_content_t %s' \
                    % self.cvars['publish-path'])

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
