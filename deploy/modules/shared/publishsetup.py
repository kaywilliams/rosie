#
# Copyright (c) 2012
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
import array
import fcntl
import platform
import re 
import socket
import string
import struct

from crypt import crypt
from random import choice

from deploy.callback   import LinkCallback
from deploy.errors     import DeployEventError
from deploy.errors     import SimpleDeployEventError
from deploy.dlogging  import L1
from deploy.util       import pps
from deploy.util       import shlib

from deploy.util.rxml  import datfile

# Include this mixin in any event that requires hostname and password 
class PublishSetupEventMixin:
  publish_mixin_version = "1.01"

  def __init__(self, *args, **kwargs):
    self.provides.add('%s-setup-options' % self.moduleid)
    self.conditionally_requires.add('publish-setup-options')
      
    for key in ['input', 'config', 'variables', 'output']:
      self.DATA.setdefault(key, [])
    self.DATA['variables'].append('publish_mixin_version')

  def setup(self):
    self.datfile = self.parse_datfile()

    # set build host 
    self.build_host = self.get_build_host()
    self.config.resolve_macros('.', {'%{build-host}': self.build_host})

    # set additional attributes
    self.localpath = self.get_local()
    self.webpath = self.get_webpath(self.build_host)
    self.domain = self.get_domain() # get_hostname() uses this for validation
    self.hostname = self.get_hostname()
    self.fqdn = self.hostname + self.domain 
    self.password = self.get_password()
    self.crypt_password = self.get_cryptpw(self.password)
    self.ssh = self.config.getbool('ssh/text()', True)
    self.ssh_passphrase = self.config.getxpath('ssh-passphrase/text()', '')
    self.boot_options = self.get_bootoptions()

    # resolve module macros
    map = {'%{url}':            {'conf':  'remote-url\' element',
                                 'value':  str(self.webpath)},
           '%{hostname}':       {'conf':  'hostname\' element',
                                 'value':  self.hostname},
           '%{domain}':         {'conf':  'domain\' element',
                                 'value':  self.domain},
           '%{fqdn}':           {'value':  self.fqdn},
           '%{password}':       {'conf':  'password\' element',
                                 'value':  self.password},
           '%{crypt-password}': {'value':  self.crypt_password},
           '%{boot-options}':   {'conf':  'boot-options\' element',
                                 'value':  self.boot_options},
           }
    for key in ['%{url}', '%{hostname}', '%{domain}', '%{fqdn}', '%{password}',
                '%{boot-options}']:
      if key in map[key]['value']:
        raise SimpleDeployEventError(
          "Macro Resolution Error: \'%s\' macro not allowed in \'%s/%s\'." %
          (key, self.moduleid, map[key]['conf']))
    self.macros = {} # making this an instance attr so dtest can access
    for key in map:
      self.macros[key] = map[key]['value']
    self.config.resolve_macros('.', self.macros)

    # ssh setup
    keyfile=pps.path('/root/.ssh/id_rsa')
    if self.ssh:
      if not keyfile.exists():
        try:
          self.log(1, L1("ssh key not found, generating"))
          cmd = '/usr/bin/ssh-keygen -t rsa -f %s -N ""' % keyfile 
          shlib.execute(cmd)
        except shlib.ShExecError, e:
          message = ("Error occurred creating ssh keys for the "
                     "root user. The error was: %s\n"
                     "If the error persists, you can generate keys manually "
                     "using the command\n '%s'" % (e, cmd))
          raise SSHFailedError(message=message)

    # set cvars
    cvars_root = '%s-setup-options' % self.moduleid
    self.cvars[cvars_root] = {}
    for attribute in ['hostname', 'domain', 'fqdn', 'password', 'ssh',
                      'ssh_passphrase', 'webpath', 'localpath', 
                      'boot_options']:
      self.cvars[cvars_root][attribute.replace('_','-')] = \
                      eval('self.%s' % attribute)

    # set DATA 
    self.DATA['config'].append('local-dir')
    self.DATA['variables'].append('localpath')
    self.DATA['config'].append('remote-url')
    self.DATA['config'].append('hostname')
    self.DATA['variables'].append('domain')
    self.DATA['variables'].append('fqdn')
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
  
  def get_build_host(self):
    ifname = self.config.getxpath('remote-url/@interface', None)
    if not ifname:
      ifname,_ = get_first_active_interface()
    try:
      build_host = get_ipaddr(ifname)
    except IOError, e:
      raise InterfaceIOError(ifname, str(e))

    if self.config.getbool('remote-url/@fqdn', 'False'):
      try:
        hostname, aliases, _ = socket.gethostbyaddr(build_host)
      except socket.herror:
        raise UnknownHostnameError(build_host, ifname) 
      names = [hostname]
      names.extend(aliases)
      for name in names:
        if '.' in name: # name is fqdn
          build_host = name
          break
      else:
        raise FQDNNotFoundError(build_host, ifname, names)

    return build_host
    
  def get_webpath(self, build_host):
    if self.moduleid == 'publish':
      default = 'repos/%s' % self.type
    else:
      default = 'repos/%s/%s' % (self.type, self.moduleid)

    remote = pps.path(self.config.getxpath('remote-url/text()', 
                      'http://'+build_host+'/'+default))
                        
    return remote / self.repoid

  def get_hostname(self):
    if self.moduleid == 'publish':
      default = self.repoid
    else:
      default = '%s-%s' % (self.repoid, self.moduleid)

    hostname = self.config.getxpath('hostname/text()', default)
    hostname = hostname.replace('_', '-') # dns doesn't allow '_' in hostnames

    # validate hostname
    if len(hostname + self.domain) > 255:
      message = "'%s' exceeds 255 characters" % hostname
      raise InvalidHostnameError(message)
    if hostname.endswith("."): # A single trailing dot is legal
      hostname = hostname[:-1] # strip trailing dot, if present

    disallowed = re.compile("[^A-Z\d-]", re.IGNORECASE)
    for label in hostname.split("."):
      if label and not len(label) <= 63: # length is not within proper range
        message = "'%s' exceeds 63 characters" % label
        raise InvalidHostnameError(message)
      if label.startswith("-"):
        message = "'%s' cannot start with '-'" % label
        raise InvalidHostnameError(message)
      if label.endswith("-"): # no bordering hyphens
        message = "'%s' cannot end with '-'" % label
        raise InvalidHostnameError(message)
      if disallowed.search(label): # contains only legal characters
        message = ( "'%s' contains an invalid character. "
                    "Valid characters are a-z, A-Z, 0-9 and '-'." % label )
        raise InvalidHostnameError(message)

    # if we got through the above, then the hostname is valid
    return hostname

  def get_domain(self):
    domain = self.config.getxpath('domain/text()', '')
    if domain and domain[0] != '.': 
      domain = '.' + domain
    return domain

  def get_bootoptions(self):
    if self.moduleid == 'publish':
      default = 'lang=en_US keymap=us'
    else:
      default = self.cvars['publish-setup-options']['boot-options']

    return self.config.getxpath('boot-options/text()', default)

  def get_password(self):
    password = self.config.getxpath('password/text()', '')
    
    if password:
      self.pwtype='user'
      return password

    else:
      self.pwtype='generated'
      return (self.datfile.getxpath('/*/%s/generated-password/text()' 
              % self.moduleid, '') or self.gen_password())

  def gen_password(self):
    size = 8 
    return ''.join([choice(
                    string.letters + string.digits) for i in range(size)])

  def get_cryptpw(self, password):
    if password == self.datfile.getxpath('/*/%s/%s-password/text()'
                                         % (self.moduleid, self.pwtype), ''):
      return self.datfile.getxpath('/*/%s/crypt-password/text()'
                                         % self.moduleid)
    else:
      return self.encrypt_password(password)

  def encrypt_password(self, password, salt=None):
    if salt is None:
      salt_pop = string.letters + string.digits + '.' + '/'
      salt = ''
      for i in range(8):
        salt = salt + choice(salt_pop)
      salt = '$6$' + salt
    return crypt(password, salt)

  def write_datfile(self):
  
    root = self.parse_datfile()
    uElement = datfile.uElement

    parent   = uElement(self.moduleid, parent=root)

    # set password
    if self.pwtype == 'user':
      userpw = uElement('user-password', parent=parent, text=self.password)
    else: 
      userpw = uElement('user-password', parent=parent, text=None)

    if self.pwtype == 'generated':
      genpw = uElement('generated-password', parent=parent, text=self.password)
    else: 
      genpw = uElement('generated-password', parent=parent, text=None)

    # set crypt-password
    cryppw = uElement('crypt-password', parent=parent, text=self.crypt_password)

    #cleanup empty nodes
    for elem in [ userpw, genpw, cryppw ]:
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
class InterfaceIOError(DeployEventError):
  message = ( "Error looking up information for interface '%(interface)s': "
              "%(message)s" )

class InvalidHostnameError(DeployEventError):
  message = "Invalid Hostname: %(message)s"

class UnknownHostnameError(DeployEventError):
  message = ( "Unable to locate a hostname for IP address '%(ipaddr)s' on "
              "on interface '%(interface)s'. Please check with your network "
              "administrator to ensure the DNS reverse record is correctly "
              "configured. Otherwise, please specify an alternative "
              "interface for obtaining the IP address. See the "
              "Deploy documentation on 'Publish' for more information.") 

class FQDNNotFoundError(DeployEventError):
  message = ( "Unable to locate a fully-qualified domain name (FQDN) for "
              "IP address '%(ipaddr)s' on interface '%(interface)s'. "
              "Valid FQDNs must contain at least one '.' to separate host "
              "and domain parts. The hostname(s) found for this address "
              "include %(hostname)s. If this IP address is correct, please "
              "check with your network administrator to ensure the DNS reverse "
              "record is correctly configured. Otherwise, please specify an "
              "alternative interface for obtaining the IP address. See the "
              "Deploy documentation on 'Publish' for more information.") 

class KeyGenerationFailed(DeployEventError):
  message = "%(message)s"
