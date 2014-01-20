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
import select
import subprocess 

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

  def _ssh_connect(self, params, **kwargs):
    # dummy command to test if a connection can be established 
    self._ssh_execute('exit', params, cmd_id="connect", **kwargs)

  def _ssh_execute(self, script, params, cmd_id=None, log_format='L2', 
                   **kwargs):
    cmd = "/usr/bin/ssh %s %s@%s %s" % (
          self._get_ssh_options(params['port'], params['key_filename']),
          params['username'], params['hostname'],
          script)
    cmd_id = cmd_id or pps.path(script).basename

    self.log(4, eval('%s' % log_format)("executing \'%s\' on host" % cmd))

    try:
      self._local_execute(cmd, cmd_id=cmd_id, **kwargs)
    except ScriptFailedError, e:
      raise SSHScriptFailedError(id=cmd_id, hostname=params['hostname'],
                                 message=e.map['errtxt'])

  def _sftp(self, cmd, params, log_format='L2', **kwargs):
    cmd = 'echo -e "%s" | /usr/bin/sftp -b - %s %s@%s' % (
          cmd,
          self._get_ssh_options(params['port'], params['key_filename']),
          params['username'], params['hostname'])

    self.log(4, eval('%s' % log_format)("executing \'%s\' on host" % cmd))

    self._local_execute(cmd, cmd_id='sftp', **kwargs)

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
        if errline: errlines.append(errline) 
      else:
        break

    if header_logged:
      self.logger.log(0, "%s" % '=' * MSG_MAXWIDTH)

    if proc.returncode:
      raise ScriptFailedError(id=cmd_id, errtxt='\n'.join(outlines + errlines))

  def _get_ssh_options(self, port, key_filename):
    return ' '.join(["-o", "StrictHostKeyChecking=no",
                     "-o", "UserKnownHostsFile=/dev/null",
                     "-o", "IdentityFile=%s" % key_filename,
                     "-o", "Port=%s" % port,
                     "-o", "ServerAliveCountMax=1",
                     "-o", "ServerAliveInterval=5",
                     "-o", "TCPKeepAlive=no",
                     "-o", "ConnectionAttempts=24",
                     "-o", "ConnectTimeout=5",
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
class ScriptFailedError(DeployEventError):
  message = "Error occured running '%(id)s':\n%(errtxt)s"

class SSHScriptFailedError(ScriptFailedError):
  def __init__(self, id, hostname, message):
    self.id = id
    self.hostname = hostname
    self.message = message

  def __str__(self):
    return ("Error(s) occured running '%s' script on '%s':\n\n"
            "%s" % (self.id, self.hostname, self.message))
