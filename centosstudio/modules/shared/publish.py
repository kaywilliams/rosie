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

from centosstudio.util import pps, shlib

class PublishEventMixin:
  def get_local(self, default):
    local = self.config.getpath('/solution/%s/local-dir/text()' % 
                                self.moduleid, default)
    return local / self.systemid
  
  def get_remote(self, default): 
    remote = pps.path(self.config.getpath('/solution/%s/remote-url/text()'
                      % self.moduleid, 
                      self._get_host(default, 'remote-url', ifname =
                        self.config.get('remote-url/@interface', None))))
    return remote / self.systemid
  
  def _get_host(self, default, xpath, ifname=None):
    if not ifname:
      ifname,_ = get_first_active_interface()
    try:
      realm = get_ipaddr(ifname)
    except IOError, e:
      raise InterfaceIOError(ifname, str(e))
  
    if self.config.getbool(xpath+'/@fqdn', 'False'):
      hostname, aliases, _ = socket.gethostbyaddr(realm)
      names = [hostname]
      names.extend(aliases)
      for name in names:
        if '.' in name: # name is fqdn
          realm = name
          break
      else:
        raise FQDNNotFoundError(realm, ifname, names)
    return 'http://'+realm+'/'+default

  def chcon(self, path):
    if self.cvars['selinux-enabled']:
      shlib.execute('chcon -R --type=httpd_sys_content_t %s' % path)

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



