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
import subprocess
import time

from decimal import Decimal

from deploy.dlogging import L2, MSG_MAXWIDTH
from deploy.errors import DeployEventError
from deploy.util import pps 

SSH_RETRIES = 24
SSH_SLEEP = 5

__all__ = ['ExecuteEventMixin',
           'ScriptFailedError', 'SSHScriptFailedError', ]

class ExecuteEventMixin:
  execute_mixin_version = "1.00"

  def __init__(self):
    self.macros = getattr(self, 'macros', {})

  def setup(self, **kwargs):
    self.DATA['variables'].append('execute_mixin_version')

  def _ssh_connect(self, params={}):
    # dummy command to test if a connection can be established 
    self._ssh_execute('exit', cmd_id="connect", params=params)

  def _ssh_execute(self, script, cmd_id=None, params={}, log_format='L2', 
                   **kwargs):
    cmd = "/usr/bin/ssh %s %s@%s %s" % (
          self._get_ssh_options(params['port'], params['key_filename']),
          params['username'], params['hostname'], script)
    cmd_id = cmd_id or pps.path(script).basename

    self.log(4, eval('%s' % log_format)("executing \'%s\' on host" % cmd))

    try:
      self._remote_execute(cmd, cmd_id=cmd_id, hostname=params['hostname'], 
                           log_format=log_format, **kwargs)
    except ScriptFailedError, e:
      raise SSHScriptFailedError(id=cmd_id, hostname=params['hostname'], 
                                 errtxt=e.errtxt)

  def _sftp(self, cmd, cmd_id=None, params={}, log_format='L2', **kwargs):
    cmd = 'echo -e "%s" | /usr/bin/sftp -b - %s %s@%s' % (
          cmd, self._get_ssh_options(params['port'], params['key_filename']), 
          params['username'], params['hostname'])
    cmd_id = cmd_id or 'sftp' 

    self.log(4, eval('%s' % log_format)("executing \'%s\' on host" % cmd))

    self._remote_execute(cmd, cmd_id=cmd_id, hostname=params['hostname'], 
                         log_format=log_format, **kwargs)

  def _remote_execute(self, cmd, cmd_id=None, hostname=None, log_format='L2',
                      **kwargs):
    """                   
    Wrapper for _local_execute that provides the hostname in log and error
    messages
    """
    self.log(4, eval('%s' % log_format)("executing \'%s\' on host" % cmd))

    try:
      self._local_execute(cmd, cmd_id=cmd_id, **kwargs)
    except ScriptFailedError, e:
      raise SSHScriptFailedError(id=cmd_id, hostname=hostname, errtxt=e.errtxt)

  def _local_execute(self, cmd, cmd_id=None, verbose=False, **kwargs):
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
                                    (self.id, cmd_id or cmd))
              header_logged = True
            self.log(0, outline)
        if errline:
          # Kludge to remove misleading ssh known hosts warning from output.
          # We are doing this because ssh doesn't provide a clean way to 
          # disable just this warning without turning off ALL warnings, many
          # others of which are useful
          if re.search(r"Warning: Permanently added '[^ ]+' \(RSA\) to the "
                        "list of known hosts.\r", errline):
            continue
          errlines.append(errline) 
      else:
        break

    if header_logged:
      self.logger.log(0, "%s" % '=' * MSG_MAXWIDTH)

    if proc.returncode:
      if not '\n'.join(errlines):
        # report exit code if no error message is returned
        errlines = ['Error: exit code %s' % proc.returncode]
      raise ScriptFailedError(id=cmd_id, errtxt='\n'.join(outlines + errlines))

  def _get_ssh_options(self, port, key_filename):
    """
    ConnectionTimeout - set this to a high value (2 minutes) to prevent
         'Name or service not known' and 'No route to host' errors while
         system is booting.
    ConnectionAttempts - set this to a high value (120 - one per second)
         to prevent 'Connection refused' and 'No route to host' errors after
         the system has booted but before the ssh daemon is up.
    """
    return ' '.join(["-o", "BatchMode=yes",
                     "-o", "StrictHostKeyChecking=no",
                     "-o", "UserKnownHostsFile=/dev/null",
                     "-o", "IdentityFile=%s" % key_filename,
                     "-o", "Port=%s" % port,
                     "-o", "ConnectTimeout=120", 
                     "-o", "ConnectionAttempts=120",
                     "-o", "ServerAliveCountMax=3",
                     "-o", "ServerAliveInterval=15",
                     "-o", "TCPKeepAlive=no",
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
class ScriptFailedError(DeployEventError):
  def __init__(self, id, errtxt):
    self.id = id
    self.errtxt = errtxt

  def __str__(self):
    return "Error occured running '%s':\n%s" % (self.id, self.errtxt)

class SSHScriptFailedError(ScriptFailedError):
  def __init__(self, id, hostname, errtxt):
    self.id = id
    self.hostname = hostname
    self.errtxt = errtxt

  def __str__(self):
    return ("Error(s) occured running '%s' script on '%s':\n"
            "%s" % (self.id, self.hostname, self.errtxt))
