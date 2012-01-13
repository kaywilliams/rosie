#
# Copyright (c) 2012
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

import paramiko
import select
import signal
import subprocess 
import sys
import traceback

from centosstudio.cslogging import L0, L1, L2
from centosstudio.errors import CentOSStudioError
from centosstudio.util import sshlib

from UserDict import DictMixin

SSH_RETRIES = 24
SSH_SLEEP = 5

class DeployEventMixin:
  deploy_mixin_version = "1.00"

  def __init__(self):
    self.requires.add('%s-setup-options' % self.moduleid)

    # we're doing this in init rather than in validate (where it 
    # should technically be) so that if no scripts are present
    # (i.e. scripts_provided is False) parent events can disable themselves.

    # setup ssh  values
    self.cvar_root = '%s-setup-options' % self.moduleid
    self.ssh = dict(
      hostname = self.cvars[self.cvar_root]['hostname'],
      port     = 22,
      username = 'root',
      password = self.cvars[self.cvar_root]['password'],
      )

    # set up script default parameters
    self.scripts = {
             'activate-script': dict(ssh=False,
                              enabled = False),
             'delete-script': dict(message='running delete script',
                              enabled = False,
                              ssh=False),
             'install-script': dict(message='running install script',
                              enabled = False,
                              ssh=False),
             'verify-install-script': 
                              dict(message='running verify-install script',
                              enabled = False,
                              ssh=True),
             'update-script': dict(message='running update script',
                              enabled = False,
                              ssh=True),
             'post-script':   dict(message='running post script',
                              enabled = False,
                              ssh=True)}


    # update scripts dict using config and validate script attributes
    self.scripts_provided = False
    for script in self.scripts:
      if self.config.get(script, None) is not None:
        # update enabled attribute
        self.scripts[script]['enabled'] = True
        self.scripts_provided = True

        # update ssh attribute
        if self.config.get('%s/@ssh' % script, []):
          self.scripts[script]['ssh'] = self.config.getbool('%s/@ssh' % script)

  def validate(self):
    # validate that hostname and password have been provided
    for script in self.scripts:
      for attribute in ['hostname', 'password']:
        if self.scripts[script]['ssh'] and not self.ssh[attribute]:
          raise DeployValidationError(id = self.id, script = script, 
                                      attribute = attribute)

  def setup(self): 
    # needs to be called after self.repomdfile and self.kstext are set

    # strip trailing whitespace from kstext so that diff testing works
    # as expected. using shelve for metadata storage (someday) will 
    # eliminate this issue
    try:
      self.kstext = self.kstext.rstrip()
    except:
      self.kstext = ''

    self.webpath = self.cvars[self.cvar_root]['webpath']

    self.DATA['variables'].extend(['webpath', 'kstext'])
    self.DATA['input'].append(self.repomdfile)

    for script in self.scripts:
      if self.scripts[script]['enabled']:
        self.io.add_xpath(script, self.mddir, destname=script, id=script, 
                          mode='750', content='text')

    for key in self.ssh:
      self.DATA['config'].append('@%s' % key)

  def run(self):
    for script in self.scripts:
      self.io.process_files(what=script)

    # set install_triggers using self.install_triggers, if provided by
    # parent event, else default to 'activate'
    try:
      install_triggers = self.install_triggers
    except:
      install_triggers = [ 'activate' ]

    if self._reinstall(triggers = install_triggers):
      self._execute('delete-script')
      self._execute('install-script')
      self._execute('activate-script')
      self._execute('verify-install-script')

    else:
      self._execute('update-script')
 
    self._execute('post-script')
 
 
  #------ Helper Functions ------#
  def _reinstall(self, triggers = []):
    '''
    Tests specified install triggers and returns true if the install script 
    should be executed. The triggers parameter accepts a list of values 
    including 'install-script', 'treeinfo', 'kickstart' and 'activate'.
    '''

    if 'release-rpm-release' in triggers:
      if 'release_rpm_release' in self.diff.variables.diffdict:
        self.log(1, L1("%s-release package changed, reinstalling" 
                       % self.name))
        return True # reinstall

    if 'config-rpm-release' in triggers:
      if 'config_rpm_release' in self.diff.variables.diffdict:
        self.log(1, L1("%s-release package changed, reinstalling" 
                       % self.name))
        return True # reinstall

    if 'install-script' in triggers:
      # did install script change (either file or text)?
      script_file = self.io.list_input(what='install-script')
      if (( script_file and script_file[0] in self.diff.input.diffdict) 
           or '/*/%s/install-script' % self.id 
           in self.diff.config.diffdict):
        self.log(1, L1("'install-script' changed, reinstalling...")) 
        return True # reinstall
  
    if 'kickstart' in triggers:
      # did kickstart change?
      if 'kstext' in self.diff.variables.diffdict:
        self.log(1, L1("kickstart changed, reinstalling...")) 
        return True # reinstall

    if 'treeinfo' in triggers:
      if 'titext' in self.diff.variables.diffdict:
        self.log(1, L1("'.treeinfo' changed, reinstalling...")) 
        return True # reinstall
      pass

    if 'activate' in triggers:
      # is there an existing system that can be activated?
      try:
        self._execute('activate-script')
      except (ScriptFailedError, SSHFailedError), e:
        self.log(1, L1(e))
        self.log(1, L1("unable to activate machine, reinstalling...")) 
        return True # reinstall

    # if not, install parameters haven't changed, no need to rebuild
    return False # don't reinstall
  
  def _execute(self, script):
    if not self.io.list_output(script): return
    if 'message' in self.scripts[script]:
      self.log(1, L1(self.scripts[script]['message']))
    cmd = self.io.list_output(what=script)[0]
    if not self.scripts[script]['ssh']: 
    # run cmd on the local machine
      r = subprocess.call(cmd, shell=True)
      if r != 0:
        raise ScriptFailedError(script=script)
      return
  
    # else run cmd on remote machine
    params = SSHParameters(self, script)
    try:
      # establish connection
      try:
        self.log(2, L2('connecting to host \'%s\'' % params['hostname'])) 
        signal.signal(signal.SIGINT, signal.default_int_handler) #enable ctrl+C
        client = sshlib.get_client(retries=SSH_RETRIES, sleep=SSH_SLEEP,
                                   callback=SSHConnectCallback(self.logger),
                                   **dict(params))

      except paramiko.BadAuthenticationType, e:
        raise SSHFailedError(script=script, message=str(e), params=str(params))

      except sshlib.ConnectionFailedError:
        raise SSHFailedError(script=script, 
          message="Unable to establish connection with remote host: '%s'"
                  % params['hostname'],
          params=str(params)) 
  
      # copy script to remote machine
      self.log(2, L2("copying '%s' to '%s'" % (script, params['hostname'])))
      sftp = paramiko.SFTPClient.from_transport(client.get_transport())
      if not 'centosstudio' in  sftp.listdir('/etc/sysconfig'): 
        sftp.mkdir('/etc/sysconfig/centosstudio')
        sftp.chmod('/etc/sysconfig/centosstudio', mode=0750)
      sftp.put(self.io.list_output(what=script)[0], 
               '/etc/sysconfig/centosstudio/%s' % script)
      sftp.chmod('/etc/sysconfig/centosstudio/%s' % script, mode=0750)
  
      # execute script
      cmd = '/etc/sysconfig/centosstudio/%s' % script
      self.log(2, L2("executing '%s' on '%s'" % (cmd, params['hostname'])))
      chan = client._transport.open_session()
      chan.exec_command(cmd)

      while True:
        r, w, x = select.select([chan], [], [], 0.0)
        if len(r) > 0:
          got_data = False
          if chan.recv_ready():
            data = chan.recv(1024)
            if data:
              got_data = True
              self.log(0, L0(data.rstrip()))
          if chan.recv_stderr_ready():
            data = chan.recv_stderr(1024)
            if data:
              got_data = True
              self.log(0, L0(data.rstrip()))
          if not got_data:
            break

      status = chan.recv_exit_status()
      chan.close()
      client.close()
      if status != 0:
        raise ScriptFailedError(script=script)
  
    except:
      if 'client' in locals():
        client.close()
      raise

    self.log(2, L2("'%s' completed successfully" % script))

class SSHParameters(DictMixin):
  def __init__(self, ptr, script):
    self.params = {}
    for param,value in ptr.ssh.items():
      self.params[param] = ptr.config.get('%s/@%s' % (script, param), value)
    self.params['hostname'] = self.params['hostname'].replace('$id',
                              ptr.solutionid)

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

class ScriptFailedError(CentOSStudioError):
  message = "Error occured running '%(script)s'. See above for error message." 

class SSHFailedError(ScriptFailedError):
  message = """Error occured running '%(script)s'.
Error message: '%(message)s'
SSH parameters: '%(params)s"""

class DeployValidationError(CentOSStudioError):
  message = """\n
[%(id)s] Validation Error: %(script)s requires a %(attribute)s for
SSH execution. Please correct using one of the following methods: 
* Set the '%(attribute)s' attribute on the '%(id)s' element. 
* Set the 'ssh' attribute to false on the '%(script)s' element.
"""

#------ Callbacks ------#
class SSHConnectCallback:
  def __init__(self, logger):
    self.logger = logger

  def start(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))

  def retry(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))
