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
import errno
import fcntl
import os
import paramiko
import select
import signal
import subprocess 
import sys
import traceback

from deploy.dlogging import L2, MSG_MAXWIDTH
from deploy.errors import DeployEventError
from deploy.util import pps
from deploy.util import sshlib 

SSH_RETRIES = 24
SSH_SLEEP = 5

__all__ = ['ExecuteEventMixin', 'ScriptFailedError', 'SSHFailedError', 
           'SSHScriptFailedError']

class ExecuteEventMixin:
  execute_mixin_version = "1.00"

  def _ssh_connect(self, params, log_format='L2'):
    try:
      try:
        self.log(2, eval('%s' % log_format)(
                         "connecting to host \'%s\'" % params['hostname'])) 
        signal.signal(signal.SIGINT, signal.default_int_handler) #enable ctrl+C
        client = sshlib.get_client(retries=SSH_RETRIES, sleep=SSH_SLEEP,
                                   callback=SSHConnectCallback(self.logger),
                                   **dict(params))

        # setting keepalive causes client to cancel processes started by the
        # server after the SSH session is terminated. It takes a few seconds for
        # the client to notice and cancel the process. 
        client.get_transport().set_keepalive(1)

      except sshlib.ConnectionFailedError, e:
        raise SSHFailedError(message=e) 

    except:
      if 'client' in locals(): client.close()
      raise

    return client

  def _ssh_execute(self, client, cmd, verbose=False, log_format='L2'):
    self.log(2, eval('%s' % log_format)("executing \'%s\' on host" % cmd))
    chan = client.get_transport().open_session()
    chan.exec_command('"%s"' % cmd)

    outlines = []
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
            outlines.extend(data.rstrip('\n').split('\n'))
            if verbose or self.logger.test(4):
              if header_logged is False:
                self.logger.log_header(0, "%s event - '%s' script output" % 
                                      (self.id, pps.path(cmd).basename))
                header_logged = True
              self.log(0, data.rstrip('\n'))
        if chan.recv_stderr_ready():
          data = chan.recv_stderr(1024)
          if data:
            got_data = True
            errlines.extend(data.rstrip('\n').split('\n'))
        if not got_data:
          break

    if header_logged:
      self.logger.log(0, "%s" % '=' * MSG_MAXWIDTH)
      self.logger.log(0, '')
      
    status = chan.recv_exit_status()
    chan.close()

    if status != 0:
      raise SSHFailedError(message='\n'.join(outlines + errlines))

  def _local_execute(self, cmd, verbose=False):
    # using shell=True which gives better error messages for scripts lacking
    # an interpreter directive (i.e. #!/bin/bash). Callers need to verify
    # that cmd does not contain arbitrary (and potentially dangerous) text.
    proc = subprocess.Popen("%s" % cmd, shell=True, stdout=subprocess.PIPE, 
                                                    stderr=subprocess.PIPE)

    self.make_async(proc.stdout)
    self.make_async(proc.stderr)

    outlines = []
    errlines = []
    header_logged = False
    while True:
      select.select([proc.stdout, proc.stderr], [], [], 0.0)
      outline = self.read_async(proc.stdout)
      errline = self.read_async(proc.stderr)
      if outline != '' or errline != '' or proc.poll() is None:
        if outline:
          outlines.append(outline)
          if verbose or self.logger.test(4): 
            if not header_logged:
              self.logger.log_header(0, "%s event - '%s' script output" %
                                    (self.id, pps.path(cmd).basename))
              header_logged = True
            self.log(0, outline)
        if errline: errlines.append(errline) 
      else:
        break

    if header_logged:
      self.logger.log(0, "%s" % '=' * MSG_MAXWIDTH)

    if proc.returncode != 0:
      raise ScriptFailedError(cmd=cmd, errtxt='\n'.join(outlines + errlines))
    return

  # Helper function to add the O_NONBLOCK flag to a file descriptor
  def make_async(self, fd):
    fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)
  
  # Helper function to read some data from a file descriptor, ignoring EAGAIN errors
  def read_async(self, fd):
    try:
      data = fd.read()
      return data.rstrip('\n')
    except IOError, e:
      if e.errno != errno.EAGAIN:
        raise e
      else:
        return ''


#------ Errors ------#
class ScriptFailedError(DeployEventError):
  message = "Error occured running '%(cmd)s'. See script output below:\n %(errtxt)s"

class SSHFailedError(ScriptFailedError):
  message = "%(message)s"

class SSHScriptFailedError(ScriptFailedError):
  message = """Error(s) occured running '%(id)s' script on '%(host)s':
%(message)s"""

#------ Callbacks ------#
class SSHConnectCallback:
  def __init__(self, logger):
    self.logger = logger

  def start(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))

  def retry(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))
