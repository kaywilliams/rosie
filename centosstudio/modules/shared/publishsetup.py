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
import string
import struct

from crypt import crypt
from random import choice

from centosstudio.modules.shared import DatfileMixin, uElement

from centosstudio.util import pps

# Include this mixin in any event that requires hostname and password 
class PublishSetupEventMixin(DatfileMixin):
  publish_mixin_version = "1.00"

  def __init__(self):
    self.provides.add('%s-setup-options' % self.moduleid)
    self.conditionally_requires.add('publish-setup-options')

    # doing everything in init so that we can define macros
    # prior to validation
    DatfileMixin.datfile_setup(self)

    self.DATA['variables'].append('publish_mixin_version')

    # set attributes
    self.localpath= self.get_local()
    self.webpath  = self.get_remote()
    self.hostname = self.get_hostname()
    self.domain   = self.get_domain()
    self.password, self.crypt_password  = self.get_password()
    self.boot_options = self.get_bootoptions()
    self.write_datfile()

    # set macros
    self.macros = {'%{url}':  str(self.webpath),
                   '%{hostname}': self.hostname,
                   '%{password}': self.password,
                   '%{crypt-password}': self.crypt_password}
    for attribute in ['domain', 'boot_options']:
      if len(eval('self.%s' % attribute)) > 0:
        self.macros['%%{%s}' % attribute.replace('_','-')] = \
                    eval('self.%s' % attribute)

    cvars_root = '%s-setup-options' % self.moduleid
    self.cvars[cvars_root] = {}
    for attribute in ['hostname', 'domain', 'password', 'webpath', 'localpath', 
                      'boot_options']:
      self.cvars[cvars_root][attribute.replace('_','-')] = \
                      eval('self.%s' % attribute)


  #------ Helper Methods ------#
  def get_local(self):
    self.DATA['config'].append('local-dir')
    self.DATA['variables'].append('localpath')
    if self.moduleid == 'publish':
      default = '/var/www/html/systems'
    else:
      default = '/var/www/html/systems/%s' % self.moduleid

    local = self.config.getpath('local-dir/text()', default)
    return local / self.systemid
  
  def get_remote(self): 
    self.DATA['config'].append('remote-url')
    self.DATA['variables'].append('webpath')
    if self.moduleid == 'publish':
      default = 'systems'
    else:
      default = 'systems/%s' % self.moduleid

    remote = pps.path(self.config.getpath('/*/%s/remote-url/text()'
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

  def get_hostname(self):
    self.DATA['config'].append('@hostname')
    if self.moduleid == 'publish':
      default = self.systemid
    else:
      default = '%s-%s' % (self.systemid, self.moduleid)

    return self.config.get('@hostname', default)

  def get_domain(self):
    self.DATA['config'].append('@domain')
    if self.moduleid == 'publish':
      default = ''
    else:
      default = self.cvars['publish-setup-options']['domain']

    return self.config.get('@domain', default)

  def get_bootoptions(self):
    self.DATA['config'].append('boot-options')
    if self.moduleid == 'publish':
      default = ''
    else:
      default = self.cvars['publish-setup-options']['boot-options']

    return self.config.get('boot-options/text()', default)

  def get_password(self):
    #print "\nmodule: ", self.moduleid
    #print "saved password: ", self.datfile.get('/*/%s/password/text()' % self.moduleid, None) 
    #print "saved cryptpw: ", self.datfile.get('/*/%s/crypt-password/text()' % self.moduleid, None)
    if self.moduleid == 'publish':
      password = (self.config.get('@password', '') or 
                  self.datfile.get('/*/%s/password/text()' % self.moduleid, '') 
                  or self.gen_password())
    else:
      password = (self.config.get('@password', '') or 
                  self.cvars['publish-setup-options']['password'])

    crypt_password = self.get_cryptpw(password)

    #print "final password: ", password
    #print "final crypt_password: ", crypt_password
    return (password, crypt_password)

  def gen_password(self):
    size = 8 
    return ''.join([choice(
                    string.letters + string.digits) for i in range(size)])

  def get_cryptpw(self, password):
    cryptpw=self.datfile.get('/*/publish/crypt-password/text()', '')

    if self.moduleid != 'publish':
      cryptpw = self.datfile.get('/*/%s/crypt-password/text()' % self.moduleid,
                                 cryptpw) 

    if len(cryptpw) > 0:
      # discard saved cryptpw if it is no longer valid
      salt = cryptpw[:11]
      if cryptpw != self.encrypt_password(password, salt):
        cryptpw = ''

    return cryptpw or self.encrypt_password(password)

  def encrypt_password(self, password, salt=None):
    if salt is None:
      salt_pop = string.letters + string.digits + '.' + '/'
      salt = ''
      for i in range(8):
        salt = salt + choice(salt_pop)
      salt = '$6$' + salt
    return crypt(password, salt)

  def write_datfile(self):
    root = self.datfile.get('/*')
    parent   = uElement(self.moduleid, parent=root)

    # set password
    if (len(self.config.get('/*/%s/@password' % self.moduleid, '')) == 0 and 
        self.moduleid == 'publish'):
      password = uElement('password', parent=parent, text=self.password)
    else:
      password = uElement('password', parent=parent, text=None)

    # set crypt_password
    if self.password != self.cvars.setdefault(
                        'publish-setup-options', {}).setdefault(
                        'password', ''):
      crypt_password = uElement('crypt-password', parent=parent, 
                       text=self.crypt_password)
    else:
      crypt_password = uElement('crypt-password', parent=parent, text=None)

    #cleanup empty nodes
    for elem in [ password, crypt_password ]:
      if elem.text == None: elem.getparent().remove(elem)
    if len(parent) == 0: parent.getparent().remove(parent)

    root.write(self.datfn, self._config.file)

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

