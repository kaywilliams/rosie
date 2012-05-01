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
from centosstudio.errors import CentOSStudioError, CentOSStudioEventError

from centosstudio.modules.shared import (ExecuteEventMixin, ScriptFailedError,
                                         SSHFailedError, SSHScriptFailedError)

from UserDict import DictMixin

class DeployEventMixin(ExecuteEventMixin):
  deploy_mixin_version = "1.02"

  def __init__(self, *args, **kwargs):
    self.requires.add('%s-setup-options' % self.moduleid,)
    self.conditionally_requires.update(['rpmbuild-data', 'release-rpm',
                                        'config-rpms'])

    # we're doing this in init rather than in validate (where it 
    # should technically be) so that if no scripts are present
    # (i.e. scripts_provided is False) parent events can disable themselves.

    # set up script default parameters
    self.scripts = {
      'trigger':      dict( ssh=True, activate=True, connect=True),
      'activate':     dict( ssh=False,),
      'install':      dict( ssh=False),
      'post-install': dict( ssh=True),
      'post':         dict( ssh=True)}

    # update scripts dict using config and validate script attributes
    self.scripts_provided = False
    for script in self.scripts:
      if self.config.getxpath(script, None) is not None: 
        # update enabled attribute
        self.scripts[script]['enabled'] = True
        self.scripts_provided = True

        # special processing for trigger element 
        if script == 'trigger':
          self.scripts[script]['activate'] = self.config.getbool(
            '%s/@activate-fails' % script, True)
          self.scripts[script]['connect'] = self.config.getbool(
            '%s/@ssh-connect-fails' % script, True)

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

    # setup ssh values
    # todo - share this with srpmbuild
    self.ssh = dict(
      enabled      = self.cvars[self.cvar_root]['ssh'],
      hostname     = self.cvars[self.cvar_root]['hostname'],
      key_filename = '/root/.ssh/id_rsa',
      port         = 22,
      username     = 'root',
      )

    for key in self.ssh:
      self.DATA['config'].append('@%s' % key)

    # setup scripts - do this before trigger macro resolution
    self.all_scripts = {} 
    for script in self.scripts:
      if self.scripts[script].setdefault('enabled', False):
        self.scripts[script]['script-ids'] = []
        self.scripts[script]['ssh-values'] = []

        scripts = self.config.xpath('%s/script' % script)
        for subscript in scripts:
          id = '%s' % subscript.getxpath('@id', '%s' % script)
          # ensure no duplicate ids
          xpath = self._configtree.getpath(subscript)
          csum = self._get_script_csum(xpath)
          index = 1
          while id in self.all_scripts and self.all_scripts[id][1] != csum:
            id = id + str(index)
            index += 1
          self.all_scripts[id] = [xpath, csum ] 

          self.scripts[script]['script-ids'].append(id)
          self.scripts[script]['ssh-values'].append(subscript.getbool('@ssh', 
                                             self.scripts[script]['ssh']))


    # resolve trigger macros 
    trigger_data = { 
      'release_rpm':         self._get_rpm_csum('release-rpm'),
      'config_rpms':         self._get_rpm_csum('config-rpms'),
      'kickstart':           self._get_csum(self.kstext),
      'treeinfo':            self._get_csum(self.cvars['base-treeinfo-text']),
      'install_scripts':     self._get_script_csum('install/script'),
      'post_install_scripts':self._get_script_csum('post-install/script'),
      }

    for key in trigger_data: 
      self.config.resolve_macros('.' , {'%%{%s}' % key: trigger_data[key]})

    triggers = self.config.getxpath('trigger/@triggers', '')
    if triggers:
      triggers = [ s.strip() for s in triggers.replace(',', ' ').split() ]
      valids = [ s.replace('_', '-') for s in trigger_data.keys() ]
      invalids = set(triggers) - set(valids)
      if invalids:
        message = ("One or more trigger specified in the definition at '%s' "
                   "is invalid. The invalid values are '%s'. Available "
                   "values are '%s'." % ( self._config.file, 
                   "', '".join(invalids), "', '".join(valids)))
        raise InvalidInstallTriggerError(message=message)
    else:
      triggers = getattr(self, 'default_install_triggers', [])

    triggers.sort()
    self.config.resolve_macros('.', {'%{triggers}': ' '.join(triggers)})

    # add data for active triggers to diff variables
    self.active_triggers = [ (x, trigger_data) for x in triggers ]
    self.DATA['variables'].append('active_triggers')

    self.deploydir = self.LIB_DIR / 'deploy'
    self.triggerfile = self.deploydir / 'trigger_info' # match script varname
    self.config.resolve_macros('.', {'%{trigger-file}': self.triggerfile})


    # setup to create script files - do this after macro resolution
    for id in self.all_scripts:
      self.io.add_xpath(self.all_scripts[id][0], self.mddir, destname=id, 
                        id=id, mode='750', content='text')

  def run(self):
    for id in self.all_scripts:
      self.io.process_files(what=id)

    self.do_clean=True # clean the deploydir once per session

    if self._reinstall():
      self.cvars['%s-reinstalled' % self.moduleid] = True # used by test cases
      if hasattr(self, 'test_fail_on_reinstall'): #set by test cases
        raise CentOSStudioError('test fail on reinstall')
      self._execute('install')
      self._execute('activate')
      self._execute('post-install')
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
    if not self.scripts['install']['enabled']:
      return False # don't try to install since we haven't got a script

    # can we activate the machine?
    if self.scripts['trigger']['activate']:
      try:
        self._execute('activate')
      except (ScriptFailedError, SSHScriptFailedError), e:
        self.log(3, L0(e))
        self.log(1, L1("unable to activate machine, reinstalling..."))
        return True # reinstall

    # can we get an ssh connection?
    if (self.ssh['enabled'] is True and 
        self.scripts['trigger']['connect']):
      params = SSHParameters(self, 'trigger')
      self.log(1, L1('attempting to connect'))
      try:
        client = self._ssh_connect(params)
        client.close()
      except SSHFailedError, e:
        self.log(3, L1(e))
        self.log(1, L1("unable to connect to machine, reinstalling...")) 
        return True # reinstall

    # does the trigger script return success?
    if self.scripts['trigger']['enabled']:
      try:
        self._execute('trigger')
      except ScriptFailedError, e:
        self.log(3, L1(str(e)))
        self.log(1, L1("trigger script failed, reinstalling..."))
        return True # reinstall

    # everything looks good
    return False # don't reinstall
  
  def _execute(self, script):
    if not self.scripts[script]['enabled']: return

    ids = self.scripts[script]['script-ids']
    for id in ids:
      cmd = self.io.list_output(what=id)[0]
      verbose = self.config.getbool('%s/script[@id="%s"]/@verbose' % 
                                   (script, id), False)
      self.log(1, L1('running %s script' % id))

      if (self.ssh['enabled'] and 
          self.scripts[script]['ssh-values'][ids.index(id)]):
        # run cmd on remote machine
        params = SSHParameters(self, script)
        try:
          try:
            client = self._ssh_connect(params)
          except SSHFailedError, e:
            raise SSHScriptFailedError(id=id, host=params['hostname'], 
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

          # copy script
          sftp.put(cmd, str( self.deploydir/cmd.basename )) # cmd is local file 
          sftp.chmod(str(self.deploydir/cmd.basename), mode=0750)
 
          # execute script
          cmd = str(self.deploydir/cmd.basename) # now cmd is remote file
          try:
            self._ssh_execute(client, cmd, verbose)
          except SSHFailedError, e:
            raise SSHScriptFailedError(id=id, host=params['hostname'],
                                       message=str(e))
  
        finally:
          if 'client' in locals(): client.close()

      else: # run cmd on the local machine
        self._local_execute(cmd, verbose)


class SSHParameters(DictMixin):
  def __init__(self, ptr, script):
    self.params = {}
    for param,value in ptr.ssh.items():
      if not param == 'enabled':
        self.params[param] = ptr.config.getxpath(
                             '%s/@%s' % (script, param), value)
    self.params['hostname'] = self.params['hostname'].replace('$id',
                              ptr.repoid)

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


#------ Errors ------#
class DeployMixinError(CentOSStudioEventError):
  message = "%(message)s"

class InvalidInstallTriggerError(DeployMixinError):
  message = "%(message)s"
