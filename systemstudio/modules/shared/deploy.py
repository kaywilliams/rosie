#
# Copyright (c) 2011
# Rendition Software, Inc. All rights reserved.
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
import signal
import socket
import sys
import time

import subprocess as sub

from systemstudio.sslogging import L0, L1, L2
from systemstudio.errors import SystemStudioError

from UserDict import DictMixin

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
                              arguments=[self.distributionid]),
             'clean-script': dict(message='cleaning machine',
                              ssh=False,
                              arguments=[self.distributionid]),
             'install-script': dict(message='installing machine',
                              ssh=False,
                              arguments=[self.distributionid, self.webpath]),
             'verify-install-script': 
                              dict(message='verifying machine installation',
                              ssh=True,
                              arguments=[self.distributionid]),
             'update-script': dict(message='updating machine',
                              ssh=True,
                              arguments=[self.distributionid]),
             'test-script': dict(message='updating machine',
                              ssh=True,
                              arguments=[self.distributionid])}

    for script in self.scripts:
      if self.config.get(script, None) is not None:
        self.io.add_xpath(script, self.mddir, destname=script, id=script, 
                          mode='750')
        self.DATA['config'].append(script)

    #setup ssh default values
    self.ssh_defaults = dict(
      hostname = self.config.get('@hostname', self.distributionid),
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

    if self._reinstall():
      self._execute('clean-script')
      self._execute('install-script')
      self._execute('activate-script')
      self._execute('verify-install-script')

    else:
      self._execute('update-script')
 
    # test
    # self._execute('test-script')
 
 
  ##### Helper Functions #####
  
  def _reinstall(self):
    '''Test install triggers and return true if system should be reinstalled'''
  
    # did install script change (either file or text)?
    script_file = self.io.list_input(what='install-script')
    if (( script_file and script_file[0] in self.diff.input.diffdict) 
         or '/distribution/%s/install-script' % self.id 
         in self.diff.config.diffdict):
      self.log(1, L1("'install-script' changed, reinstalling...")) 
      return True
  
    # did kickstart change?
    if 'kstext' in self.diff.variables.diffdict:
      self.log(1, L1("kickstart changed, reinstalling...")) 
      return True

    # is there an existing system that can be activated?
    try:
      self._execute('activate-script')
    except (ScriptFailedError, SSHFailedError), e:
      self.log(1, L1(e))
      self.log(1, L1("unable to activate machine, reinstalling...")) 
      return True

    # if not, install parameters haven't changed, no need to rebuild
    return False 
  
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
      client = paramiko.SSHClient()
      client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
      signal.signal(signal.SIGINT, signal.default_int_handler) #enable ctrl+C
      self.log(2, L2('connecting to host \'%s\'' % params['hostname'])) 
      for i in range(24): # retry connect to host every 5 seconds for 2 minutes
        try:
          client.connect(**dict(params))
          break
        except (socket.error, paramiko.SSHException), e:
          if i == 0:
            self.log(2, L2("Unable to connect. System may be starting. Will retry for 2 minutes. Press CTRL+C to exit."))
          self.log(2, L2("%s. Retrying..." % e))
          time.sleep(5)

        except paramiko.BadAuthenticationType, e:
          raise SSHFailedError(script=script, message=str(e), 
                               params=str(params))

        # host can change from installation to installation, so 
        # don't require a match to known hosts
        except paramiko.BadHostKeyException:
          pass 
  
      else:
        raise SSHFailedError(script=script, 
          message="unable to establish connection with remote host: '%s'"
                  % params['hostname'],
          params=str(params)) 
  
      # copy script to remote machine
      self.log(2, L2("copying '%s' to '%s'" % (script, params['hostname'])))
      sftp = paramiko.SFTPClient.from_transport(client.get_transport())
      if not '.systemstudio' in  sftp.listdir(): 
        sftp.mkdir('.systemstudio')
        sftp.chmod('.systemstudio', mode=0750)
      sftp.put(self.io.list_output(what=script)[0], '.systemstudio/%s' % script)
      sftp.chmod('.systemstudio/%s' % script, mode=0750)
  
      # execute script
      cmd = './.systemstudio/%s %s' % (script, 
            ' '.join(self.scripts[script]['arguments']))
      self.log(2, L2("executing '%s' on '%s'" % (cmd, params['hostname'])))
      chan = client._transport.open_session()
      chan.exec_command(cmd)
      stdin = chan.makefile('wb', -1)
      stdout = chan.makefile('rb', -1)
      stderr = chan.makefile_stderr('rb', -1)
      for f in ['out', 'err']:
        text = eval('std%s.read()' % f).rstrip()
        if text:
          self.log(0, L0(text))
      status = chan.recv_exit_status()
      chan.close()
      client.close()
      if status != 0:
        raise ScriptFailedError(script=script)
  
    except Exception, e:
      print e
      try: client.close()
      except: pass
      raise

class SSHParameters(DictMixin):
  def __init__(self, ptr, script):
    self.params = {}
    for param,value in ptr.ssh_defaults.items():
      self.params[param] = ptr.config.get('%s/@%s' % (script, param), value)

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

class ScriptFailedError(SystemStudioError):
  message = "Error occured running '%(script)s'. See above for error message." 

class SSHFailedError(ScriptFailedError):
  message = """Error occured running '%(script)s'.
Error message: '%(message)s'
SSH parameters: '%(params)s"""

