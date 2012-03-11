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
import string
import struct

from crypt import crypt
from random import choice

from centosstudio.errors import CentOSStudioEventError
from centosstudio.errors import SimpleCentOSStudioEventError
from centosstudio.util   import pps
from centosstudio.util.rxml import datfile

# Include this mixin in any event that requires hostname and password 
class PublishSetupEventMixin:
  publish_mixin_version = "1.00"

  def __init__(self, *args, **kwargs):
    self.provides.add('%s-setup-options' % self.moduleid)
    self.conditionally_requires.add('publish-setup-options')
    self.DATA['variables'].append('publish_mixin_version')

  def setup(self):
    self.datfile = datfile.parse(basefile=self._config.file)

    # set attributes
    self.localpath = self.get_local()
    self.webpath = self.get_remote()
    self.hostname = self.get_hostname()
    self.password = self.get_password()
    self.ssh = self.config.get('@ssh', True)
    self.crypt_password = self.get_cryptpw(self.password)
    self.boot_options = self.get_bootoptions()

    # resolve module macros
    map = {'%{url}':            {'conf':  'remote-url\' element',
                                  'value':  str(self.webpath)},
           '%{hostname}':       {'conf':  '@hostname\' attribute',
                                  'value':  self.hostname},
           '%{password}':       {'conf':  '@password\' attribute',
                                  'value':  self.password},
           '%{crypt-password}': {'value':  self.crypt_password},
           '%{boot-options}':   {'conf':  'boot-options\' element',
                                  'value':  self.boot_options},
           }
    for key in ['%{url}', '%{hostname}', '%{password}', '%{boot-options}']:
      if key in map[key]['value']:
        raise SimpleCentOSStudioEventError(
          "Macro Resolution Error: \'%s\' macro not allowed in \'%s/%s\'." %
          (key, self.moduleid, map[key]['conf']))
    self.macros = {} # making this an instance attr so cstest can access
    for key in map:
      self.macros[key] = map[key]['value']
    self.config.resolve_macros('.', self.macros)

    # set cvars
    cvars_root = '%s-setup-options' % self.moduleid
    self.cvars[cvars_root] = {}
    for attribute in ['hostname', 'password', 'ssh', 
                      'webpath', 'localpath', 'boot_options']:
      self.cvars[cvars_root][attribute.replace('_','-')] = \
                      eval('self.%s' % attribute)

    # set DATA 
    self.DATA['config'].append('local-dir')
    self.DATA['variables'].append('localpath')
    self.DATA['config'].append('remote-url')
    self.DATA['config'].append('@hostname')
    self.DATA['config'].append('boot-options')

    self.write_datfile()

  #------ Helper Methods ------#
  def get_local(self):
    if self.moduleid == 'publish':
      default = '/var/www/html/repos/%s' % self.type
    else:
      default = '/var/www/html/repos/%s/%s' % (self.type, self.moduleid)

    local = self.config.getpath('local-dir/text()', default)
    return local / self.repoid
  
  def get_remote(self): 
    if self.moduleid == 'publish':
      default = 'repos/%s' % self.type
    else:
      default = 'repos/%s/%s' % (self.type, self.moduleid)

    remote = pps.path(self.config.getpath('remote-url/text()',
                      self._get_host(default, 'remote-url', ifname =
                        self.config.get('remote-url/@interface', None))))
    if self.moduleid == 'publish':
      return remote / self.repoid / 'os'
    else:
      return remote / self.repoid
  
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
    if self.moduleid == 'publish':
      default = self.repoid
    else:
      default = '%s-%s' % (self.repoid, self.moduleid)

    return self.config.get('@hostname', default)

  def get_bootoptions(self):
    if self.moduleid == 'publish':
      default = 'lang=en_US keymap=us'
    else:
      default = self.cvars['publish-setup-options']['boot-options']

    return self.config.get('boot-options/text()', default)

  def get_password(self):
    if self.moduleid == 'publish':
      password = (self.config.get('@password', '') or 
                  self.datfile.get('/*/%s/password/text()' % self.moduleid, ''))
      if not password:
        password = self.gen_password()
    else:
      password = (self.config.get('@password', '') or 
                  self.cvars['publish-setup-options']['password'])

    return password

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
  
    root = datfile.parse(basefile=self._config.file)
    uElement = datfile.uElement

    parent   = uElement(self.moduleid, parent=root)

    # set password
    if (len(self.config.get('@password', '')) == 0 and 
        self.moduleid == 'publish'):
      password = uElement('password', parent=parent, text=self.password)
    else:
      password = uElement('password', parent=parent, text=None)

    # set crypt_password
    if (self.moduleid == 'publish' or 
        self.password != self.cvars.setdefault(
                         'publish-setup-options', {}).setdefault(
                         'password', '')):
      crypt_password = uElement('crypt-password', parent=parent, 
                       text=self.crypt_password)
    else:
      crypt_password = uElement('crypt-password', parent=parent, text=None)

    #cleanup empty nodes
    for elem in [ password, crypt_password ]:
      if elem.text == None: elem.getparent().remove(elem)
    if len(parent) == 0: parent.getparent().remove(parent)

    root.write()

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


#------ Error Classes ------#
class InterfaceIOError(CentOSStudioEventError):
  message = ( "Error looking up information for interface '%(interface)s': "
              "%(message)s" )

class FQDNNotFoundError(CentOSStudioEventError):
  message = ( "Unable to locate a fully-qualified domain name (FQDN) for "
              "IP address '%(ipaddr)s' on interface '%(interface)s'. "
              "Valid FQDNs must contain at least one '.' to separate host "
              "and domain parts. The hostname(s) found for this address "
              "include %(hostname)s. If this IP address is correct, please "
              "check with your network administrator to ensure the DNS reverse "
              "record is correctly configured. Otherwise, please specify an "
              "alternative interface for obtaining the IP address. See the "
              "CentOS Studio documentation on 'Publish' for more information.") 
