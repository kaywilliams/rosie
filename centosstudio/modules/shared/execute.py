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

import paramiko
import select
import signal
import subprocess 
import sys
import traceback

from centosstudio.cslogging import L0, L1, L2
from centosstudio.errors import CentOSStudioEventError
from centosstudio.util import sshlib


SSH_RETRIES = 24
SSH_SLEEP = 5

class ExecuteMixin:
  execute_mixin_version = "1.00"

  def setup(self):
    self.DATA['variables'].append('execute_mixin_version')


  def _execute_local(self, script):
    "execute a script file on the local machine"
    proc = subprocess.Popen(script, shell=True, stdout=subprocess.PIPE, 
                                                stderr=subprocess.PIPE)
  
    errlines = []
    header_logged = False
    while True:
      outline = proc.stdout.readline().rstrip()
      errline = proc.stderr.readline().rstrip()
      if outline != '' or errline != '' or proc.poll() is None:
        if outline: 
          if not header_logged:
            self.logger.log_header(4, "%s event - begin '%s' output" %
                                  (self.id, script.basename))
            header_logged = True
          self.log(4, L0(outline))
        if errline: errlines.append(errline) 
      else:
        break
  
    if header_logged:
      self.logger.log_footer(4, "%s event - end '%s' output" % (
                                 self.id, script.basename))
  
    if proc.returncode != 0:
      raise ScriptFailedError(script=script.basename, 
                              errtxt='\n'.join(errlines))
    return
   
   
  def _execute_remote(self, cmd, params):
    "run cmd on a remote machine using SSH"
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
      self.log(2, L2("copying %s to host" % script))
      sftp = paramiko.SFTPClient.from_transport(client.get_transport())
      if not 'centosstudio' in  sftp.listdir('/etc/sysconfig'): 
        sftp.mkdir('/etc/sysconfig/centosstudio')
        sftp.chmod('/etc/sysconfig/centosstudio', mode=0750)
      sftp.put(self.io.list_output(what=script)[0], 
               '/etc/sysconfig/centosstudio/%s' % script)
      sftp.chmod('/etc/sysconfig/centosstudio/%s' % script, mode=0750)
   
      # setting keepalive causes client to cancel processes started by the
      # server after the SSH session is terminated. It takes a few seconds for
      # the client to notice and cancel the process. 
      client.get_transport().set_keepalive(1)
  
      # execute script
      cmd = '/etc/sysconfig/centosstudio/%s' % script
      self.log(2, L2("executing '%s' on host" % cmd))
      chan = client.get_transport().open_session()
      chan.exec_command(cmd)
  
      errlines = []
      header_logged = False
      while True:
        r, w, x = select.select([chan], [], [], 0.0)
        if len(r) > 0:
          got_data = False
          if chan.recv_ready():
            data = chan.recv(1024)
            if data:
              got_data = True
              if header_logged is False:
                self.logger.log_header(4, "%s event - begin '%s' output" % 
                                      (self.id, script))
                header_logged = True
              self.log(4, L0(data.rstrip('\n')))
          if chan.recv_stderr_ready():
            data = chan.recv_stderr(1024)
            if data:
              got_data = True
              errlines.extend(data.rstrip('\n').split('\n'))
          if not got_data:
            break
  
      if header_logged:
        self.logger.log_footer(4, "%s event - end '%s' output" % 
                               (self.id, script))
        
      status = chan.recv_exit_status()
      chan.close()
      client.close()
      if status != 0:
        raise ScriptFailedError(script=script, errtxt='\n'.join(errlines))
    
    except:
      if 'client' in locals():
        client.close()
      raise

  def _execute_remote_sftp(self, cmd, params):
    "run cmd on a remote machine using SFTP"
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
      self.log(2, L2("copying %s to host" % script))
      sftp = paramiko.SFTPClient.from_transport(client.get_transport())
      if not 'centosstudio' in  sftp.listdir('/etc/sysconfig'): 
        sftp.mkdir('/etc/sysconfig/centosstudio')
        sftp.chmod('/etc/sysconfig/centosstudio', mode=0750)
      sftp.put(self.io.list_output(what=script)[0], 
               '/etc/sysconfig/centosstudio/%s' % script)
      sftp.chmod('/etc/sysconfig/centosstudio/%s' % script, mode=0750)
   
      # setting keepalive causes client to cancel processes started by the
      # server after the SSH session is terminated. It takes a few seconds for
      # the client to notice and cancel the process. 
      client.get_transport().set_keepalive(1)
  
      # execute script
      cmd = '/etc/sysconfig/centosstudio/%s' % script
      self.log(2, L2("executing '%s' on host" % cmd))
      chan = client.get_transport().open_session()
      chan.exec_command(cmd)
  
      errlines = []
      header_logged = False
      while True:
        r, w, x = select.select([chan], [], [], 0.0)
        if len(r) > 0:
          got_data = False
          if chan.recv_ready():
            data = chan.recv(1024)
            if data:
              got_data = True
              if header_logged is False:
                self.logger.log_header(4, "%s event - begin '%s' output" % 
                                      (self.id, script))
                header_logged = True
              self.log(4, L0(data.rstrip('\n')))
          if chan.recv_stderr_ready():
            data = chan.recv_stderr(1024)
            if data:
              got_data = True
              errlines.extend(data.rstrip('\n').split('\n'))
          if not got_data:
            break
  
      if header_logged:
        self.logger.log_footer(4, "%s event - end '%s' output" % 
                               (self.id, script))
        
      status = chan.recv_exit_status()
      chan.close()
      client.close()
      if status != 0:
        raise ScriptFailedError(script=script, errtxt='\n'.join(errlines))
    
    except:
      if 'client' in locals():
        client.close()
      raise

  def _connect(self, hostname,)
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
    

class ScriptFailedError(CentOSStudioEventError):
  message = "Error occured running '%(script)s'. See error message below:\n %(errtxt)s" 

class SSHFailedError(ScriptFailedError):
  message = """Error occured running '%(script)s'.
Error message: '%(message)s'
SSH parameters: '%(params)s"""

class DeployValidationError(CentOSStudioEventError):
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
