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

import paramiko
import select
import signal
import sys
import traceback

import subprocess as sub

from centosstudio.sslogging import L0, L1, L2
from centosstudio.errors import CentOSStudioError
from centosstudio.util import sshlib

from UserDict import DictMixin

SSH_RETRIES = 24
SSH_SLEEP = 5

class DeployEventMixin:
  def setup(self): 
    # needs to be called after self.webpath, self.repomdfile and self.kstext
    # are set

    # strip trailing whitespace from kstext so that diff testing works
    # as expected. using shelve for metadata storage (someday) will 
    # eliminate this issue
    self.kstext = self.kstext.rstrip()

    self.DATA['variables'].extend(['webpath', 'kstext'])
    self.DATA['input'].append(self.repomdfile)

    self.scripts = {
             'activate-script': dict(ssh=False, 
                              arguments=[self.solutionid]),
             'clean-script': dict(message='running clean script',
                              ssh=False,
                              arguments=[self.solutionid]),
             'install-script': dict(message='running install script',
                              ssh=False,
                              arguments=[self.solutionid, self.webpath]),
             'verify-install-script': 
                              dict(message='running verify-install script',
                              ssh=True,
                              arguments=[self.solutionid]),
             'update-script': dict(message='running update script',
                              ssh=True,
                              arguments=[self.solutionid]),
             'post-script':   dict(message='running post script',
                              ssh=True,
                              arguments=[self.solutionid])}

    for script in self.scripts:
      if self.config.get(script, None) is not None:
        self.io.add_xpath(script, self.mddir, destname=script, id=script, 
                          mode='750')
        self.DATA['config'].append(script)

    #setup ssh default values
    _hostname = self.config.get('@hostname', self.solutionid)
    self.ssh_defaults = dict(
      hostname = _hostname.replace('$id', self.solutionid),
      port     = self.config.get('@port', 22),
      username = self.config.get('@username', 'root'),
      password = self.config.get('@password', None),
      #TODO - add remaining ssh parameters
      )

    for key in self.ssh_defaults:
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
      self._execute('clean-script')
      self._execute('install-script')
      self._execute('activate-script')
      self._execute('verify-install-script')

    else:
      self._execute('update-script')
 
    self._execute('post-script')
 
 
  ##### Helper Functions #####
  
  def _reinstall(self, triggers = []):
    '''
    Tests specified install triggers and returns true if the install script 
    should be executed. The triggers parameter accepts a list of values 
    including 'install-script', 'kickstart' and 'activate'.
    '''
  
    if 'install-script' in triggers:
      # did install script change (either file or text)?
      script_file = self.io.list_input(what='install-script')
      if (( script_file and script_file[0] in self.diff.input.diffdict) 
           or '/solution/%s/install-script' % self.id 
           in self.diff.config.diffdict):
        self.log(1, L1("'install-script' changed, reinstalling...")) 
        return True # reinstall
  
    if 'kickstart' in triggers:
      # did kickstart change?
      if 'kstext' in self.diff.variables.diffdict:
        self.log(1, L1("kickstart changed, reinstalling...")) 
        return True # reinstall

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
    cmd = '%s %s' % (self.io.list_output(what=script)[0], 
                     ' '.join(self.scripts[script]['arguments']))
    if not self.config.get('%s/@ssh' % script, self.scripts[script]['ssh']): 
    # run cmd on the local machine
      r = sub.call(cmd, shell=True)
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
      if not '.centosstudio' in  sftp.listdir(): 
        sftp.mkdir('.centosstudio')
        sftp.chmod('.centosstudio', mode=0750)
      sftp.put(self.io.list_output(what=script)[0], '.centosstudio/%s' % script)
      sftp.chmod('.centosstudio/%s' % script, mode=0750)
  
      # execute script
      cmd = './.centosstudio/%s %s' % (script, 
            ' '.join(self.scripts[script]['arguments']))
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

class SSHParameters(DictMixin):
  def __init__(self, ptr, script):
    self.params = {}
    for param,value in ptr.ssh_defaults.items():
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


class SSHConnectCallback:
  def __init__(self, logger):
    self.logger = logger

  def start(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))

  def retry(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))

