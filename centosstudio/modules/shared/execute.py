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

from centosstudio.cslogging import L2, MSG_MAXWIDTH
from centosstudio.errors import CentOSStudioEventError
from centosstudio.util import pps
from centosstudio.util import sshlib 

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

    errlines = []
    header_logged = False
    while True:
      outline = proc.stdout.readline().rstrip()
      errline = proc.stderr.readline().rstrip()
      if outline != '' or errline != '' or proc.poll() is None:
        if outline and (verbose or self.logger.test(4)): 
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
      raise ScriptFailedError(cmd=cmd, errtxt='\n'.join(errlines))
    return


#------ Errors ------#
class ScriptFailedError(CentOSStudioEventError):
  message = "Error occured running '%(cmd)s'. See error message below:\n %(errtxt)s"

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
