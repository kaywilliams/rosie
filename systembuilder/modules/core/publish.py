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
import array
import fcntl
import platform
import socket
import struct

from rendition import pps
from rendition import shlib

from systembuilder.errors    import SpinError
from systembuilder.event     import Event
from systembuilder.logging   import L1

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
      'variables': ['distributionid'],
      'config': ['.'],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.local  = pps.path(self.config.getpath('local-dir',  '/var/www/html/distributions'))
    self.remote = pps.path(self.config.getpath('remote-url',
                    self._get_host(ifname =
                      self.config.get('remote-url/@interface', None))))

  def apply(self):
    self.cvars['publish-content'] = set()
    self.cvars['publish-path'] = self.local / self.distributionid
    self.cvars['web-path'] = self.remote / self.distributionid

  def _get_host(self, ifname=None):
    if self.config.getbool('remote-url/@use-hostname', 'False'):
      realm = socket.gethostname()
    else:
      if not ifname:
        ifname,_ = get_first_active_interface()
      try:
        realm = get_ipaddr(ifname)
      except IOError, e:
        raise InterfaceIOError(ifname, str(e))
    return 'http://'+realm+'/distributions'

# TODO - improve these, they're pretty vulnerable to changes in offsets and
# the like
def get_ipaddr(ifname='eth0'):
  "Get the ip address associated with the given device ifname"
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  return socket.inet_ntoa(fcntl.ioctl(
                            s.fileno(),
                            0x8915, # SIOCGIFADDR
                            struct.pack('256s', ifname[:15]))[20:24])

def get_first_active_interface():
  "Return the ifname, ifaddr for the first active non-loopback interface"
  for ifname, ifaddr in get_interfaces():
    if ifaddr.startswith('127.'): # loopback
      continue
    return ifname, ifaddr
  return None, None

def get_interfaces():
  "Return a list (ifname, ifaddr) tuples for all active network intefaces"
  noffset = 32; roffset = 32
  if platform.machine() == 'x86_64': # x86_64 has different offsets, yay
    noffset = 16; roffset = 40
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  bytes = 128 * 32 # 128 interfaces x # bytes in the struct?
  names = array.array('B', '\0' * bytes)
  outbytes = struct.unpack('iL', fcntl.ioctl(
    s.fileno(),
    0x8912, # SIOCGIFCONF
    struct.pack('iL', bytes, names.buffer_info()[0])
  ))[0]
  namestr = names.tostring()
  return ( [ ( namestr[i:i+noffset].split('\0', 1)[0],
               socket.inet_ntoa(namestr[i+20:i+24]) )
             for i in range(0, outbytes, roffset) ] )

class PublishEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish',
      parentid = 'all',
      requires = ['publish-path', 'publish-content'],
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

  # overriding Event method to remove publish-path which is outside
  # the mddir this is a hack, better would be to generalize
  # clean_eventcache to clean all event output, not just output in the
  # metadata dir.
  def clean(self):
    Event.clean(self)
    self.cvars['publish-path'].rm(recursive=True, force=True)

  def run(self):
    "Publish the contents of SOFTWARE_STORE to PUBLISH_STORE"
    self.io.sync_input(link=True,
                       text="publishing to '%s'" % self.cvars['publish-path'])
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


class InterfaceIOError(SpinError):
  message = ( "Error looking up information for interface '%(interface)s': "
              "%(message)s" )
