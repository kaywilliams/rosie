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
import socket
import sys
import time

import subprocess as sub

from systemstudio.sslogging import L0, L1, L2, L3
from systemstudio.errors import SystemStudioError

from UserDict import DictMixin

class DeployEventMixin:
  def setup(self): # needs to be called after self.webpath is set
    self.scripts = {
             'activate-script': dict(ssh=False, 
                              arguments=[self.distributionid]),
             'clean-script': dict(message='cleaning machine',
                              message_level='2',
                              message_format='L2',
                              ssh=False,
                              arguments=[self.distributionid]),
             'install-script': dict(message='installing machine',
                              message_level='2',
                              message_format='L2',
                              ssh=False,
                              arguments=[self.distributionid, self.webpath]),
             'verify-install-script': 
                              dict(message='verifying machine installation',
                              message_level='2',
                              message_format='L2',
                              ssh=True,
                              arguments=[self.distributionid]),
             'update-script': dict(message='updating machine',
                              message_level='2',
                              message_format='L2',
                              ssh=True,
                              arguments=[self.distributionid]),
             'test-script': dict(message='updating machine',
                              message_level='2',
                              message_format='L2',
                              ssh=True,
                              arguments=[self.distributionid])}

    for script in self.scripts:
      if self.config.get(script, None) is not None:
        self.io.add_xpath(script, self.mddir, destname=script, id=script, 
                          mode='750')

  def run(self):
    for script in self.scripts:
      self.io.process_files(what=script)

    if not self._rebuild() and (not self.io.list_output('activate_script') 
                           or self._execute('activate-script')):
       self.log(1, L1("running update script"))
       r = self._execute('update-script')
       if r != 0: sys.exit(1)
 
    # install
    else:
      self.log(1, L1("running install script"))
      #self.io.list_output('clean-script') and self._execute('clean-script')
      #self.io.list_output('install-script') and self._execute('install-script')
      self.io.list_output('activate-script') and self._execute(
        'activate-script')
      self.io.list_output('verify-install-script') and self._execute(
        'verify-install-script')
 
    # test
    # self.log(1, L1("running test script"))
    # self._execute('test-script')
 
 
  ##### Helper Functions #####

  def _rebuild(self):
    '''Test current rebuild triggers against prior and return true if changes'''

    # did install script change (either file or text)?
    script_file = self.io.list_input(what='install-script')
    if (( script_file and script_file[0] in self.diff.input.diffdict) 
         or '/distribution/test/install-script' in self.diff.config.diffdict):
      return True
  
    # did kickstart change?
    if 'kstext' in self.diff.variables.diffdict: 
      return True

    # did installer files change?
    for f in self.installer_files:
      if f in self.diff.input.diffdict:
        return True
      
    # if not, install parameters haven't changed, no need to rebuild
    return False 

  def _execute(self, script):
    if 'message' in self.scripts[script]:
      self.log(self.scripts[script]['message_level'], 
               eval("%s('%s')" % (self.scripts[script]['message_format'],
               self.scripts[script]['message'])))
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
      client.load_system_host_keys()
      client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      for i in range(24): # retry connect to host every 5 seconds for 2 minutes
        try:
          client.connect(**params)
          break
        except socket.error as e:
          if e[0] == 4:
            raise KeyboardInterrupt
          else:
            self.log(1, 
              L0("[socket.error %s] %s: System may be starting. Will continue retrying for 2 minutes. Press CTRL+C twice to exit"
              % (e[0], e[1])))
            time.sleep(5)
        except paramiko.BadAuthenticationType as e:
          raise SSHFailedError(script=script, message=str(e), 
                               params=str(params))
      else:
        raise SSHFailedError(script=script, 
          message="unable to establish connection with remote host: '%s'"
                  % params['hostname'],
          params=str(params)) 

      # copy script to remote machine
      sftp = paramiko.SFTPClient.from_transport(client.get_transport())
      if not '.systemstudio' in  sftp.listdir(): sftp.mkdir('.systemstudio')
      sftp.put(self.io.list_output(what=script)[0], '.systemstudio/%s' % script)
      sftp.chmod('.systemstudio/%s' % script, mode=0755)

      # execute script
      chan = client._transport.open_session()
      chan.exec_command('.systemstudio/%s %s' % 
                        (script, ' '.join(self.scripts[script]['arguments'])))
      stdin = chan.makefile('wb', -1)
      stdout = chan.makefile('rb', -1)
      stderr = chan.makefile_stderr('rb', -1)
      for f in ['out', 'err']:
        print eval('std%s.read()' % f)
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
    self.params = dict(
      hostname=ptr.config.get('%s/@hostname' % script, 
                    ptr.config.get('@hostname', ptr.distributionid)),
      port=ptr.config.get('%s/@port' % script, 
                    ptr.config.get('@port', '22')),
      username=ptr.config.get('%s/@username' % script,
                    ptr.config.get('@username', 'root')),
      password=ptr.config.get('%s/@password' % script,
                    ptr.config.get('@password')),
    #TODO - add remaining ssh parameters
    )
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
  message = "Error occured running '%(script)s'. Please correct and try again. See above for error message." 

class SSHFailedError(ScriptFailedError):
  message = """Error occured running '%(script)s'. Please correct and try again.
Error message: '%(message)s'
SSH parameters: '%(params)s"""

