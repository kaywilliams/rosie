#
# Copyright (c) 2013
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
import errno 
import hashlib
import paramiko
import re

from deploy.dlogging import L0, L1
from deploy.errors import (DeployError, DeployEventError,
                                 DuplicateIdsError)
from deploy.util import pps 
from deploy.util import resolve 

from deploy.util.pps.Path.error import PathError

from deploy.modules.shared import (InputEventMixin, ExecuteEventMixin,
                                   ScriptFailedError,
                                   SSHFailedError, SSHScriptFailedError)
# InputEventMixin loads ExecuteEventMixin

from deploy.util.graph import DirectedNodeMixin

from UserDict import DictMixin

RELEASE_PKG_CSUM = 'release_pkg_csum'
CUSTOM_PKGS_CSUM = 'custom_pkgs_csum'
KICKSTART_CSUM = 'kickstart_csum'
TREEINFO_CSUM = 'treeinfo_csum'
INSTALL_SCRIPTS_CSUM = 'install_scripts_csum'
POST_INSTALL_SCRIPTS_CSUM = 'post_install_scripts_csum'

class DeployEventMixin(InputEventMixin, ExecuteEventMixin):
  deploy_mixin_version = "1.02"

  def __init__(self, reinstall=False, *args, **kwargs):
    self.requires.update(['%s-setup-options' % self.moduleid],)
    self.conditionally_requires.update(['rpmbuild-data', 'release-rpm',
                                        'config-rpms', 'srpmbuild', 
                                        '%s-ksname' % self.moduleid,
                                        '%s-ksfile' % self.moduleid])
    self.reinstall = reinstall # forces reinstall on event run
    ExecuteEventMixin.__init__(self)

  def setup(self): 
    InputEventMixin.setup(self)
    ExecuteEventMixin.setup(self)
    self.DATA['variables'].extend(['deploy_mixin_version'])

    self.cvar_root = '%s-setup-options' % self.moduleid

    self.webpath = self.cvars[self.cvar_root]['webpath']

    # get os_url - same as webpath unless user specified in the definition
    self.os_url = pps.path(self.config.getxpath('os-url/text()', None))
    if self.os_url:
      self.io.validate_input_file(self.os_url)
    else:                     
      self.os_url = self.webpath
    self.resolve_macros(map={'%{os-url}': self.os_url})

    # add repomd as input file
    self._track_repomdfile()

    # ssh setup
    keyfile=pps.path('/root/.ssh/id_rsa')
    self.ssh = dict(
      enabled      = self.cvars[self.cvar_root]['ssh'],
      hostname     = self.cvars[self.cvar_root]['fqdn'],
      key_filename = '%s' % keyfile,
      password     = self.cvars[self.cvar_root]['ssh-passphrase'],
      port         = 22,
      username     = 'root',
      )

    for key in self.ssh:
      self.DATA['config'].append('@%s' % key)

    self.ssh_defaults = { 'test-triggers': True,
                          'activate': False,
                          'delete': False,
                          'install': False,
                          'post-install': True, 
                          'save-triggers': True, 
                          'post': True } 

    # setup types - do this before trigger macro resolution
    self.scripts = {} 
    self.types = {} 
    for type in self.ssh_defaults:
      self.types[type] = [] # updated later if scripts exist
      scripts = self.config.xpath('script[@type="%s"]' % type, [])
      if scripts:
        resolver = resolve.Resolver()

        for script in scripts:
          id = script.getxpath('@id') # id required in schema
          if id in self.scripts:
            raise DuplicateIdsError(element='script', id=id)
          ssh = script.getbool('@ssh', self.ssh_defaults[type])
          verbose = script.getbool('@verbose', False)
          xpath = 'script[@id="%s"]' % id
          csum = self._get_script_csum(xpath)
          for x in ['comes-before', 'comes-after']:
            reqs = script.getxpath('@%s' % x, '')
            exec ("%s = [ s.strip() for s in reqs.replace(',', ' ').split() ]"
                   % x.replace('-', '_'))
          item = Script(id, ssh, verbose, xpath, csum, comes_before, 
                        comes_after)
          resolver.add_node(item)
          self.scripts[id] = item

        self.types[type] = resolver.resolve()

    # raise an error if any script requires ssh and ssh is disabled
    if not self.ssh['enabled']:
      for script in self.scripts.values():
        if script.ssh:
          message = ("The deployment script with the id '%s' requires SSH "
                     "connectivity, but SSH has been disabled using the "
                     "'%s/ssh' element." % (script.id, self.moduleid)) 
          raise SSHFailedError(message=message)

    # resolve trigger macros
    self.trigger_data = { 
      RELEASE_PKG_CSUM:          self._get_release_pkg_csum(),
      CUSTOM_PKGS_CSUM:          self._get_custom_pkgs_csum(),
      KICKSTART_CSUM:            self._get_kickstart_csum(),
      TREEINFO_CSUM:             self._get_treeinfo_csum(),
      INSTALL_SCRIPTS_CSUM:      self._get_script_csum('script[ '
                                                   '@type="install"]'),
      POST_INSTALL_SCRIPTS_CSUM: self._get_script_csum('script[ '
                                                    '@type="post-install" or '
                                                    '@type="save-triggers" or '
                                                    '@type="post"]'),
      }
    self.DATA['variables'].append('trigger_data')

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

    self.resolve_macros(map={'%{triggers}': triggers,
                             '%{custom-pkgs}': self._get_custom_pkgs()})

    self.deploydir = self.LIB_DIR / 'deploy'
    self.triggerfile = self.deploydir / 'trigger_info' # match type varname
    self.resolve_macros(map={'%{trigger-file}': self.triggerfile})

    # setup to create type files - do this after macro resolution
    for scripts in self.types.values():
      for script in scripts:
        self.io.add_xpath(script.xpath, self.mddir, destname=script.id, 
                          id=script.id, mode='750', content='text')

  def run(self):
    InputEventMixin.run(self)

    for scripts in self.types.values():
      for script in scripts:
        self.io.process_files(what=script.id)

    self.do_clean=True # clean the deploydir once per session

    if self._reinstall():
      if hasattr(self, 'test_fail_on_reinstall'): #set by test cases
        raise DeployError('test fail on reinstall')
      self._execute('delete')
      self._execute('install')
      self._execute('activate')
      self._execute('post-install')
      self._execute('save-triggers')
      self._execute('post')

    else:
      self._execute('activate')
      self._execute('post')
 
 
  #------ Helper Functions ------#
  def _track_repomdfile(self):
    mdfile = 'repodata/repomd.xml'
    self.repomdfile = self.os_url / mdfile
    try:
      self.link(self.repomdfile, self.mddir) # cache for offline support
    except PathError, e:
      if e.errno == errno.ENOENT:
        raise InvalidDistroError(self.os_url, mdfile)
      else: raise
    self.DATA['input'].append(self.repomdfile)

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
    ksname = self.cvars['%s-ksname' % self.moduleid]
    if ksname and (self.webpath/ksname).exists():
      kstext = (self.webpath/ksname).read_text()
    else:
      kstext = ''
    return self._get_csum(kstext)

  def _get_treeinfo_csum(self):
    tifile = self.os_url / '.treeinfo'
    if not self.type == 'package':
      try:
        return self._get_csum(tifile.read_text())
      except PathError, e:
        if e.errno == errno.ENOENT:
          raise InvalidDistroError(self.os_url, tifile)
        else: raise
    else:
      return self._get_csum('')

  def _get_script_csum(self, xpath):
    text = ''
    for script in self.config.xpath(xpath, []):
      text = text + script.getxpath('text()', '')
    return self._get_csum(text) 

  def _get_custom_pkgs(self):
    if 'rpmbuild-data' in self.cvars:
      pkgs = [] 
      for rpm in self.cvars['rpmbuild-data']:
        if rpm == '%s-release' % self.name: # ignore release rpm
          pass
        else:
          pkgs.append(rpm)
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

    # can we activate the machine?
    if self.config.getbool('triggers/@activate', True):
      try:
        self._execute('activate')
      except (ScriptFailedError, SSHScriptFailedError), e:
        self.log(3, L0(e))
        self.log(1, L1("unable to activate machine, reinstalling..."))
        return True # reinstall

    # can we get an ssh connection?
    if self.ssh['enabled'] and self.config.getbool('triggers/@connect', True):
      params = SSHParameters(self, 'test-triggers')
      self.log(1, L1('attempting to connect'))
      try:
        client = self._ssh_connect(params)
        client.close()
      except SSHFailedError, e:
        self.log(3, L1(e))
        self.log(1, L1("unable to connect to machine, reinstalling...")) 
        return True # reinstall

    # does the trigger type return success?
    if self.types['test-triggers']:
      try:
        self._execute('test-triggers')
      except ScriptFailedError, e:
        self.log(3, L1(str(e)))
        self.log(1, L1("test-trigger script failed, reinstalling..."))
        return True # reinstall

    # everything looks good
    return False # don't reinstall
  
  def _execute(self, type):
    if not self.types[type]: return

    for script in self.types[type]:
      cmd = self.io.list_output(what=script.id)[0]
      self.log(1, L1('running %s script' % script.id))

      if self.ssh['enabled'] and script.ssh:
        # run cmd on remote machine
        params = SSHParameters(self, type)
        try:
          try:
            client = self._ssh_connect(params)
          except SSHFailedError, e:
            raise SSHScriptFailedError(id=script.id, host=params['hostname'], 
                                       message=str(e))

          # create sftp client
          sftp = paramiko.SFTPClient.from_transport(client.get_transport())

          # create libdir
          if not self.LIB_DIR.basename in sftp.listdir(str(
                                          self.LIB_DIR.dirname)):
            try:
              sftp.mkdir(str(self.LIB_DIR))
            except IOError, e:
              raise RemoteFileCreationError(msg=
                "An error occurred creating the script directory '%s' "
                "on the remote system '%s'. %s"
                % (self.LIB_DIR, params['hostname'], str(e)))

          # create deploydir
          if not (self.deploydir.basename in 
                  sftp.listdir(str(self.deploydir.dirname))): 
            sftp.mkdir(str(self.deploydir))
            sftp.chmod(str(self.deploydir), mode=0750)

          # clean deploydir - except for trigger file
          if self.do_clean:
            files = sftp.listdir(str(self.deploydir))
            if self.triggerfile.basename in files:
              files.remove(str(self.triggerfile.basename))
            for f in files:
              sftp.remove(str(self.deploydir/f))
            self.do_clean = False # only clean once per session

          # copy type
          sftp.put(cmd, str( self.deploydir/cmd.basename )) # cmd is local file 
          sftp.chmod(str(self.deploydir/cmd.basename), mode=0750)
 
          # execute type
          cmd = str(self.deploydir/cmd.basename) # now cmd is remote file
          try:
            self._ssh_execute(client, cmd, script.verbose)
          except SSHFailedError, e:
            raise SSHScriptFailedError(id=script.id, host=params['hostname'],
                                       message=str(e))
  
        finally:
          if 'client' in locals(): client.close()

      else: # run cmd on the local machine
        self._local_execute(cmd, script.verbose)


class Script(resolve.Item, DirectedNodeMixin):
  def __init__(self, id, ssh, verbose, xpath, csum, comes_before, comes_after):
    self.id = id
    self.ssh = ssh
    self.verbose = verbose 
    self.xpath = xpath
    self.csum = csum
    resolve.Item.__init__(self, id, 
                          conditionally_comes_before=comes_before,
                          conditionally_comes_after=comes_after)

    DirectedNodeMixin.__init__(self)


class SSHParameters(DictMixin):
  def __init__(self, ptr, type):
    self.params = {}
    for param,value in ptr.ssh.items():
      if not param == 'enabled':
        self.params[param] = ptr.config.getxpath(
                             '%s/@%s' % (type, param), value)

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

class RemoteFileCreationError(DeployEventError):
  message = ("%(msg)s")

class InvalidDistroError(DeployEventError):
  message = ("The repository at '%(system)s' does not appear to be "
             "valid. The following file could not be found: '%(missing)s'")

class InvalidTriggerNameError(DeployEventError):
  message = ("Invalid character in trigger name '%(trigger)s'. Valid "
             "characters are a-z, A-Z, 0-9 and _.")
