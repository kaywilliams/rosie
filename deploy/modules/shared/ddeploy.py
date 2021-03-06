#
# Copyright (c) 2015
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
import hashlib
import re
import socket

from deploy.dlogging import L0, L1
from deploy.errors import (DeployError, DeployEventError,
                           DuplicateIdsError, ConfigError,
                           REGEX_ID, InvalidIdError)
from deploy.util import pps
from deploy.util import resolve
from deploy.util import shlib
from deploy.util.graph import GraphCycleError

from deploy.util.pps.Path.error import PathError

from deploy.util.rxml import config

from deploy.modules.shared import (InputEventMixin, ExecuteEventMixin,
                                   ScriptFailedError, SSHScriptFailedError,
                                   validate_hostname, InvalidHostnameError)

from deploy.util.graph import DirectedNodeMixin

from UserDict import DictMixin

RELEASE_PKG_CSUM = 'release_pkg_csum'
CUSTOM_PKGS_CSUM = 'custom_pkgs_csum'
KICKSTART_CSUM = 'kickstart_csum'
TREEINFO_CSUM = 'treeinfo_csum'
INSTALL_SCRIPTS_CSUM = 'install_scripts_csum'
POST_INSTALL_SCRIPTS_CSUM = 'post_install_scripts_csum'

DEPLOYMENT_MODULES = [ 'test-install', 'test-update', 'publish' ]

class DeployEventMixin(InputEventMixin, ExecuteEventMixin):
  deploy_mixin_version = "1.02"

  def __init__(self, reinstall=False, track_repomd=True, *args, **kwargs):
    self.requires.add('sshsetup')
    self.requires.add('%s-setup-options' % self.moduleid)
    self.conditionally_requires.update(['rpmbuild-data', 'release-rpm',
                                        'config-rpms', 'srpmbuild',
                                        'treeinfo-text',
                                        '%s-ksname' % self.moduleid,
                                        '%s-ksfile' % self.moduleid])
    self.reinstall = reinstall # forces reinstall on event run
    self.track_repomd = track_repomd # used by test-install to prevent
                                     # reinstall on repomd changes
    ExecuteEventMixin.__init__(self)

  def setup(self): 
    InputEventMixin.setup(self)
    ExecuteEventMixin.setup(self)

    self.DATA['variables'].update(['deploy_mixin_version'])
    self.DATA['config'].update(['script', 'triggers'])

    self.cvar_root = '%s-setup-options' % self.moduleid

    self.webpath = self.cvars[self.cvar_root]['webpath']
    self.ssh_host_file = self.datfn.dirname / 'ssh-host-%s' % self.moduleid
    self.ssh_host_key_file = (self.datfn.dirname /
                              'ssh-host-key-%s' % self.moduleid)

    macros={'%{ssh-host-file}': self.ssh_host_file,
            '%{ssh-host-key-file}': self.ssh_host_key_file}
    if self.cvars.get('config-dir', None):
      macros['%{config-dir}'] = self.cvars['config-dir']

    self.resolve_macros(map=macros)

    # add repomd as input file
    if self.track_repomd:
      self.DATA['input'].add(self.cvars[self.cvar_root]['repomdfile'])

    # ssh setup
    keyfile=pps.path('/root/.ssh/id_rsa')
    self.ssh = dict(
      hostname     = None, # filled in from self.hostname_defaults (below) 
      key_filename = '%s' % keyfile,
      port         = 22,
      username     = 'root',
      )

    # set ssh host defaults
    self.hostname_defaults = { 
                           'pre': 'localhost',
                           'test-exists': 'localhost',
                           'activate': 'localhost',
                           'test-triggers': '%{ssh-host}',
                           'delete': 'localhost',
                           'pre-install': 'localhost', 
                           'install': 'localhost',
                           'post-install': '%{ssh-host}', 
                           'save-triggers': '%{ssh-host}',
                           'update': '%{ssh-host}', 
                           'post': '%{ssh-host}'
                           }

    # setup types - do this before trigger macro resolution
    self.scripts = {} 
    self.types = {} 
    for type in self.hostname_defaults:
      self.types[type] = [] # updated later if scripts exist
      scripts = self.config.xpath('script[@type="%s"]' % type, [])
      if scripts:
        resolver = resolve.Resolver()

        for script in scripts:
          modules = script.get('modules',
                               self.moduleid).replace(',', ' ').split()
          for m in modules:
            if m not in DEPLOYMENT_MODULES:
              raise InvalidModuleError(m, script)
          if self.moduleid not in modules:
            continue
          id = script.getxpath('@id') # id required in schema

          # validate
          if not REGEX_ID.match(id):
            raise InvalidIdError(script) 
          if id in self.scripts:
            if script == self.config.getxpath(self.scripts[id].xpath):
              continue # elem exactly matches a previous elem, ignore
            else:
              elems = self.config.xpath('script[@id="%s"]' % id)
              raise DuplicateIdsError(elems)

          hostname = script.getxpath('@hostname', None)
          known_hosts_file = script.getxpath('@known-hosts-file',
                                             self.ssh_host_key_file) 
          verbose = script.getbool('@verbose', False)
          xpath = 'script[@id="%s"]' % id
          for x in ['comes-before', 'comes-after']:
            reqs = script.getxpath('@%s' % x, '')
            exec ("%s = [ s.strip() for s in reqs.replace(',', ' ').split() ]"
                   % x.replace('-', '_'))
          item = Script(id, hostname, known_hosts_file, verbose, xpath,
                        comes_before, comes_after)
          resolver.add_node(item)
          self.scripts[id] = item

        try:
          self.types[type] = resolver.resolve()
        except GraphCycleError as e:
          msg = ("Error resolving 'comes-before' and 'comes-after' "
                 "dependencies in scripts:\n\n%s" % e)
          raise ScriptGraphCycleError(msg=msg)

    # resolve trigger macros
    self.trigger_data = { 
      RELEASE_PKG_CSUM:          self._get_release_pkg_csum(),
      CUSTOM_PKGS_CSUM:          self._get_custom_pkgs_csum(),
      KICKSTART_CSUM:            self._get_kickstart_csum(),
      TREEINFO_CSUM:             self._get_treeinfo_csum(),
      INSTALL_SCRIPTS_CSUM:      self._get_script_csum(
                                 [ s.xpath for s in 
                                   self.types['pre'] +
                                   self.types['pre-install'] +
                                   self.types['install'] ] ),
      POST_INSTALL_SCRIPTS_CSUM: self._get_script_csum(
                                 [ s.xpath for s in 
                                   self.types['post-install'] +
                                   self.types['save-triggers'] +
                                   self.types['update'] +
                                   self.types['post'] ] ),
      }
    self.DATA['variables'].add('trigger_data')

    for key in self.trigger_data:
      self.resolve_macros(map={'%%{%s}' % key: self.trigger_data[key]})

    triggers = self.config.getxpath('triggers/text()',
               ' '.join(getattr(self, 'default_install_triggers',
                        [ RELEASE_PKG_CSUM, CUSTOM_PKGS_CSUM, KICKSTART_CSUM,
                          TREEINFO_CSUM, INSTALL_SCRIPTS_CSUM, 
                          POST_INSTALL_SCRIPTS_CSUM ])))

    for trigger in triggers.split():
      if not re.match('^[a-zA-Z0-9_]+$', trigger):
        raise InvalidTriggerNameError(trigger)

    self.resolve_macros(map={
      '%{triggers}': triggers,
      '%{trigger-file}': '%{script-data-dir}/trigger_info',
      '%{custom-pkgs}': self._get_custom_pkgs()})

    # setup to create type files - do this after macro resolution
    for scripts in self.types.values():
      for script in scripts:
        self.io.add_xpath(script.xpath, self.mddir, destname=script.id,
                          id=script.id, mode='750', content='text')

  def run(self):
    InputEventMixin.run(self)

    for scripts in self.types.values():
      for script in scripts:
        if self.io.list_output(what=script.id)[0].exists():
          # force script to be recopied on each run to support per-script 
          # post-processing (i.e. %{script-id} and %{ssh-host} macro resolution)
          self.io.list_output(what=script.id)[0].remove()
        self.io.process_files(what=script.id)

    if self._reinstall():
      if hasattr(self, 'test_fail_on_reinstall'): #set by test cases
        raise DeployError('test fail on reinstall')
      self._write_install_status_start()
      self._execute('pre')
      self._execute('delete')
      self._execute('pre-install')
      self._execute('install')
      self._execute('activate')
      self._execute('post-install')
      self._execute('save-triggers')
      self._write_install_status_complete()
      self._execute('update')
      self._execute('post')

    else:
      self._execute('pre')
      self._execute('activate')
      self._execute('update')
      self._execute('post')

 
  #------ Helper Functions ------#
  def _get_csum(self, text):
    return hashlib.md5(text).hexdigest()

  def _get_release_pkg_csum(self):
    if 'rpmbuild-data' in self.cvars and \
       '%s-release' % self.name in self.cvars['rpmbuild-data']:
      return self._get_csum(self.cvars['rpmbuild-data']
                                      ['%s-release' % self.name]
                                      ['rpm-release'])
    else: 
      return self._get_csum('')

  def _get_custom_pkgs_csum(self):
    if 'rpmbuild-data' in self.cvars:
      releases = [] 
      for rpm, data in self.cvars['rpmbuild-data'].items():
        if rpm == '%s-release' % self.name: # ignore release rpm
          pass
        else:
          releases.append(data['rpm-release'])
          releases.sort()
      return self._get_csum(''.join(releases)) # simple way to determine if any
                                               # custom packages have changed
    else: 
      return self._get_csum('')

  def _get_kickstart_csum(self):
    ksfile = self.cvars['%s-ksfile' % self.moduleid]
    if ksfile:
      kstext = ksfile.read_text()
    else:
      kstext = ''
    return self._get_csum(kstext)

  def _get_treeinfo_csum(self):
    if not self.type == 'package':
      return self._get_csum(self.cvars['treeinfo-text'])
    else:
      return self._get_csum('')

  def _get_script_csum(self, xpaths):
    text = ''
    for xpath in sorted(xpaths):
      for script in self.config.xpath(xpath, []):
        text = text + script.getxpath('text()', '')
    return self._get_csum(text) 

  def _get_custom_pkgs(self):
    if 'rpmbuild-data' in self.cvars:
      pkgs = [] 
      for rpm, data in self.cvars['rpmbuild-data'].items():
        if rpm == '%s-release' % self.name: # ignore release rpm
          pass
        else:
          pkgs.append('%s-%s-%s.%s' % (data['rpm-name'], data['rpm-version'],
                                       data['rpm-release'], data['rpm-arch']))
          pkgs.sort()
      return ' '.join(pkgs)
    else: 
      return ''

  def _reinstall(self):
    if not self.types['install']:
      return False # don't try to install since we haven't got any scripts

    # is the reinstall property set?
    if self.reinstall:
      return True

    # does the machine exist?
    try:
      self._execute('test-exists')
    except (ScriptFailedError, SSHScriptFailedError), e:
      if self.config.getbool('triggers/@exists', True) and e.returncode == 3:
        self.log(4, e)
        self.log(1, L1("test-exists script returned exit code 3, "
                       "reinstalling..."))
        return True # reinstall
      else:
        raise

    # did previous install terminate prior to completion?
    if self.parse_datfile().getxpath(
       '/*/%s/install-status/text()' % self.moduleid, None) == "incomplete":
      self.log(1, L1("previous install terminated prior to completion, reinstalling..."))
      return True

    # can we activate it?
    try:
      self._execute('activate')
    except (ScriptFailedError, SSHScriptFailedError), e:
      if self.config.getbool('triggers/@activate', False) and e.returncode == 3:
        self.log(4, e)
        self.log(1, L1("activation script returned exit code 3, "
                       "reinstalling..."))
        return True # reinstall
      else:
        raise

    # do test-trigger-type scripts return success?
    if self.types['test-triggers']:
      try:
        self._execute('test-triggers')
      except ScriptFailedError, e:
        if e.returncode == 3:
          self.log(3, L1(e))
          self.log(1, L1("test-trigger returned exit code 3, reinstalling..."))
          return True # reinstall
        else:
          raise

    # everything looks good
    return False # don't reinstall
  
  def _execute(self, type):
    if not self.types[type]: return

    for script in self.types[type]:
      cmd = self.io.list_output(what=script.id)[0]
      self.log(1, L1('running %s script' % script.id))

      # resolve per-script macros
      script_text = cmd.read_text()
      map = { '%{script-id}': script.id,
              '%{ssh-host}': self.get_ssh_host() }
      for k,v in map.items():
        script_text = script_text.replace(k,v)
      cmd.write_text(script_text)

      # get SSHParameters
      params = SSHParameters(self, type)
      params['hostname'] = script.hostname or params['hostname']
      if '%{ssh-host}' in params['hostname']:
        params['hostname'] = self.get_ssh_host()
      params['known_hosts_file'] = script.known_hosts_file

      # execute local script
      if params['hostname'] == 'localhost':
        # execute script on local machine
        self._local_execute(cmd, script_id=script.id, verbose=script.verbose)

      # execute ssh script
      else:
        # ensure known_hosts_file exists
        if not pps.path(script.known_hosts_file).exists():
          msg = ("Error validating attributes for the '%s' script:\n\n"
                 "The known-hosts-file '%s' could not be found."
                 % (script.id, script.known_hosts_file))
          raise MissingKnownHostsFileError(msg=msg)
 
        # execute script
        self._remote_execute(cmd, script_id=script.id, params=params, 
                                      verbose=script.verbose)

  def _write_install_status_start(self):
    root = self.parse_datfile()
    parent = root.getxpath('./%s' % self.moduleid)
    elem = parent.getxpath('install-status',  
                           config.uElement('install-status', parent=parent))
    elem.text = "incomplete"
    self.write_datfile(root)

  def _write_install_status_complete(self):
    root = self.parse_datfile()
    elem = root.getxpath('./%s/install-status' % self.moduleid)
    elem.text = "complete"
    self.write_datfile(root)

  def get_ssh_host(self):
    if self.ssh_host_file.exists():
      try:
        ssh_host = None # start clean as ssh_host_file contents can change
        ssh_host = self.ssh_host_file.read_text().strip()
      except Exception as e:
        message = ("Unable to read hostname file '%s'. The error was '%s'"
                   % (self.ssh_host_file, e))
        raise SshHostFileError(msg=message)
      # validate hostname, unless it is an ipaddress
      if not re.match(ssh_host, '\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'):
        try:
          validate_hostname(ssh_host)
        except InvalidHostnameError as e:
          message = ("Invalid Hostname in ssh-host-file at '%s'. The error "
                     "was %s" % (self.ssh_host_file, e))
          raise SshHostFileError(msg=message)
    else:
      ssh_host = self.cvars[self.cvar_root]['fqdn'] 
  
    return ssh_host

class Script(resolve.Item, DirectedNodeMixin):
  def __init__(self, id, hostname, known_hosts_file, verbose, xpath, 
               comes_before, comes_after):
    self.id = id
    self.hostname = hostname
    self.known_hosts_file = known_hosts_file
    self.verbose = verbose 
    self.xpath = xpath
    resolve.Item.__init__(self, id, 
                          conditionally_comes_before=comes_before,
                          conditionally_comes_after=comes_after)

    DirectedNodeMixin.__init__(self)

  def __str__(self):
    return self.id


class SSHParameters(DictMixin):
  """
  provides default ssh parameters by script type - eliminate in future
  and handle in _execute method?
  """

  def __init__(self, ptr, type):
    self.params = {}
    for param,value in ptr.ssh.items():
      if param == 'hostname':
        self.params['hostname'] = ptr.hostname_defaults[type]
      else:
        self.params[param] = value

  def __getitem__(self, key):
    return self.params[key]
 
  def __setitem__(self, key, item):
    self.params[key] = item
 
  def __delitem__(self, key):
    self.params[key].clear()
 
  def keys(self):
    return self.params.keys()    

  def __str__(self):
    return ', '.join([ '%s=\'%s\'' % (k,self.params[k]) for k in self.params ])

class ScriptGraphCycleError(DeployEventError):
  message = "%(msg)s"

class SshHostFileError(DeployEventError):
  message = "%(msg)s"

class InvalidModuleError(ConfigError):
  def __init__(self, module, elem):
    self.module = module
    ConfigError.__init__(self, elem)

  def __str__(self):
    return ("Validation Error: invalid module name '%s' while validating "
            "the following element:\n%s" % (self.module, self.errstr))

class InvalidTriggerNameError(DeployEventError):
  message = ("Invalid character in trigger name '%(trigger)s'. Valid "
             "characters are a-z, A-Z, 0-9 and _.")

class MissingKnownHostsFileError(DeployEventError):
  message = "%(msg)s"
