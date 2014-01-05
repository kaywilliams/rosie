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
import fcntl
import os
import re
import select
import signal
import subprocess 
import sys
import time
import traceback

from decimal import Decimal

from deploy.dlogging import L2, MSG_MAXWIDTH
from deploy.errors import DeployEventError
from deploy.util import pps 

SSH_RETRIES = 24
SSH_SLEEP = 5

__all__ = ['ExecuteEventMixin', 'SSHConnectionFailedError',
           'ScriptFailedError', 'SSHScriptFailedError', ]

class ExecuteEventMixin:
  execute_mixin_version = "1.00"

  def __init__(self):
    self.macros = getattr(self, 'macros', {})

  def setup(self, **kwargs):
    self.DATA['variables'].append('execute_mixin_version')

  def _ssh_connect(self, params, log_format='L2', **kwargs):
    # dummy command to just to confirm a connection is possible 
    self._ssh_execute('exit', params, **kwargs)

  def _ssh_execute(self, script, params, **kwargs):
    cmd = "/usr/bin/ssh %s %s@%s %s" % (
          self._get_ssh_options(params['port'], params['key_filename']),
          params['username'], params['hostname'],
          script)

    try:
      self._remote_execute(cmd, params, **kwargs)
    except ScriptFailedError, e:
      raise SSHScriptFailedError(script=script, hostname=params['hostname'],
                                 message=e.map['errtxt'])

  def _sftp(self, cmd, params, **kwargs):
    cmd = 'echo -e "%s" | /usr/bin/sftp -b - %s %s@%s' % (
          cmd,
          self._get_ssh_options(params['port'], params['key_filename']),
          params['username'], params['hostname'])

    self._remote_execute(cmd, params, **kwargs)

  def _remote_execute(self, cmd, params, retries=24, sleep=5, verbose=False,
                      log_format='L2'):
    """                   
    Wrapper for _local_execute that retries ssh commands for a timeout period
    in case the system is starting.

    * retries -  specifies the number of time to retry the connection
    * sleep - specifies the time in seconds to sleep between each retry
    
    The defaults are 24 and 5, respectively, for a total wait period of 2
    mintues. 
    """
    self.log(4, eval('%s' % log_format)("executing \'%s\' on host" % cmd))

    for i in range(retries): # retry connect
      try:
        self._local_execute(cmd, verbose=verbose)
        break
      except SSHError, e:
        if i == 0:
          max = Decimal(retries) * sleep / 60
          message = ("Unable to connect to %s. System may be starting. "
                     "Will retry for %s minutes." % (params['hostname'], max))
          self.logger.log(2, L2(message))
        message = str(e).split(': ')[-1].strip() # strip ssh error prefix
        self.logger.log(2, L2("%s. Retrying..." % message))
        time.sleep(sleep)

    else:
      raise SSHConnectionFailedError(str(e), params)

  def _local_execute(self, cmd, verbose=False):
    try:
      # using shell=True which gives better error messages for scripts lacking
      # an interpreter directive (i.e. #!/bin/bash).
      _PIPE = subprocess.PIPE
      proc = subprocess.Popen(cmd, stdin=_PIPE, stdout=_PIPE, stderr=_PIPE,
                              close_fds=True, shell=True)

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

      if proc.returncode:
        if errlines and re.search(r'^ssh\:', errlines[0]):
          raise SSHError('\n'.join(outlines + errlines))
        else:
          raise ScriptFailedError(cmd, errtxt='\n'.join(outlines + errlines))
      return

    # Kill subprocesses, especially ssh, and any children. The goal is to 
    # circumvent native ssh connection timeout handling and ensure consistent
    # connect handling via _remote_execute. 
    except KeyboardInterrupt as e:
      try:
        os.killpg(proc.pid, signal.SIGTERM)  # kill subprocess and children
      except OSError: # e.g. No such process
        pass
      raise e

  def _get_ssh_options(self, port, key_filename):
    return ' '.join(["-o", "StrictHostKeyChecking=no",
                     "-o", "UserKnownHostsFile=/dev/null",
                     "-o", "IdentityFile=%s" % key_filename,
                     "-o", "Port=%s" % port,
                     "-o", "ServerAliveCountMax=1",
                     "-o", "ServerAliveInterval=5",
                     "-o", "TCPKeepAlive=no",
                     "-o", "ConnectionAttempts=1",
                     "-o", "ConnectTimeout=0",
                     "-o", "LogLevel=ERROR",
                     ])

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
class SSHError(Exception):
  pass

class SSHConnectionFailedError(Exception):
  def  __init__(self, message, params):
    self.hostname = params['hostname']
    self.message = message
    self.params = ', '.join([ '%s=\'%s\'' % (k,params[k]) 
                              for k in params ])

  def __str__(self):
    return ("Unable to establish connection with remote host: '%s':\n"
            "Error Message: %s\n"
            "SSH Parameters: %s" 
            % (self.hostname, self.message, self.params))


class ScriptFailedError(DeployEventError):
  message = "Error occured running '%(cmd)s':\n%(errtxt)s"


class SSHScriptFailedError(ScriptFailedError):
  def __init__(self, script, hostname, message):
    self.script = script
    self.hostname = hostname
    self.message = message

  def __str__(self):
    return ("Error(s) occured running '%s' script on '%s':\n\n"
            "%s" % (self.script, self.hostname, self.message))
