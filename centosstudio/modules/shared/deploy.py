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
import hashlib
import paramiko

from centosstudio.cslogging import L0, L1
from centosstudio.errors import CentOSStudioError, DuplicateIdsError 
from centosstudio.util import pps
from centosstudio.util import resolve 

from centosstudio.modules.shared import (ExecuteEventMixin, ScriptFailedError,
                                         SSHFailedError, SSHScriptFailedError)

from centosstudio.util.graph import DirectedNodeMixin

from UserDict import DictMixin

class DeployEventMixin(ExecuteEventMixin):
  deploy_mixin_version = "1.02"

  def __init__(self, *args, **kwargs):
    self.requires.add('%s-setup-options' % self.moduleid,)
    self.conditionally_requires.update(['rpmbuild-data', 'release-rpm',
                                        'config-rpms'])

  def setup(self): 
    # needs to be called after self.repomdfile and self.kstext are set
    self.cvar_root = '%s-setup-options' % self.moduleid

    # strip trailing whitespace from kstext so that diff testing works
    # as expected. using shelve for metadata storage (someday) will 
    # eliminate this issue
    try:
      self.kstext = self.kstext.rstrip()
    except:
      self.kstext = ''

    self.webpath = self.cvars[self.cvar_root]['webpath']

    self.DATA['variables'].extend(['webpath', 'kstext', 'deploy_mixin_version'])
    self.DATA['input'].append(self.repomdfile)

    # ssh setup
    if self.cvars[self.cvar_root]['ssh']:
      keyfile=pps.path('/root/.ssh/id_rsa')
      if not keyfile.exists():
        message = ("SSH not correctly configured on this "
                   "machine. The '%s' file does not exist. See the CentOS "
                   "Studio documentation for information on configuring build "
                   "and client systems for remote command execution using SSH."
                   % keyfile)
        raise SSHFailedError(message=message)

    self.ssh = dict(
      enabled      = self.cvars[self.cvar_root]['ssh'],
      hostname     = self.cvars[self.cvar_root]['fqdn'],
      key_filename = '%s' % keyfile,
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
          xpath = self._configtree.getpath(script)
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

    # resolve trigger macros 
    trigger_data = { 
      'release_rpm':          self._get_rpm_csum('release-rpm'),
      'config_rpms':          self._get_rpm_csum('config-rpms'),
      'kickstart':            self._get_csum(self.kstext),
      'treeinfo':             self._get_csum(self.cvars['base-treeinfo-text']),
      'install_scripts':      self._get_script_csum('script[@type="install"]'),
      'post_install_scripts': self._get_script_csum('script[ '
                                                    '@type="post-install" or '
                                                    '@type="save-triggers"]'),
      }

    for key in trigger_data: 
      self.config.resolve_macros('.' , {'%%{%s}' % key: trigger_data[key]})

    self.triggers = self.config.xpath('triggers/trigger/text()',
         ['activate', 'connect' ] + getattr(self, 'default_install_triggers', 
         []))

    # don't include activate and connect in triggers macro
    macro_triggers = list(set(self.triggers) - set(['activate', 'connect']))
    macro_triggers.sort()
    self.config.resolve_macros('.', {'%{triggers}': ' '.join(macro_triggers)})

    # add data for active triggers to diff variables
    self.active_triggers = [ (x, trigger_data) for x in macro_triggers ]
    self.DATA['variables'].append('active_triggers')

    self.deploydir = self.LIB_DIR / 'deploy'
    self.triggerfile = self.deploydir / 'trigger_info' # match type varname
    self.config.resolve_macros('.', {'%{trigger-file}': self.triggerfile})


    # setup to create type files - do this after macro resolution
    for scripts in self.types.values():
      for script in scripts:
        self.io.add_xpath(script.xpath, self.mddir, destname=script.id, 
                          id=script.id, mode='750', content='text')

  def run(self):
    for scripts in self.types.values():
      for script in scripts:
        self.io.process_files(what=script.id)

    self.do_clean=True # clean the deploydir once per session

    if self._reinstall():
      if hasattr(self, 'test_fail_on_reinstall'): #set by test cases
        raise CentOSStudioError('test fail on reinstall')
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
  def _get_csum(self, text):
    return hashlib.md5(text).hexdigest()

  def _get_rpm_csum(self, id):
    if not 'rpmbuild-data' in self.cvars or not self.cvars[id]:
      return self._get_csum('')
    rpms = self.cvars[id]
    if isinstance(rpms, basestring):
      rpms = [ rpms ]
    releases = []
    for rpm in rpms:
      releases.append(self.cvars['rpmbuild-data'][rpm]['rpm-release'])
    if releases:
      releases.sort()
      return self._get_csum(''.join(releases)) # simple way to determine if
                                               # any release numbers have
                                               # changed
    else:
      return self._get_csum('')

  def _get_script_csum(self, xpath):
    text = ''
    for script in self.config.xpath(xpath, []):
      text = text + script.getxpath('text()', '')
    return self._get_csum(text) 

  def _reinstall(self):
    if not self.types['install']:
      return False # don't try to install since we haven't got any scripts

    # can we activate the machine?
    if 'activate' in self.triggers:
      try:
        self._execute('activate')
      except (ScriptFailedError, SSHScriptFailedError), e:
        self.log(3, L0(e))
        self.log(1, L1("unable to activate machine, reinstalling..."))
        return True # reinstall

    # can we get an ssh connection?
    if self.ssh['enabled'] and 'connect' in self.triggers:
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
            sftp.mkdir(str(self.LIB_DIR))

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

