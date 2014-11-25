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
import sys

from subprocess import Popen, PIPE
from threading  import Thread

from StringIO import StringIO

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

  def _get_ssh_options(self, port, key_filename):
    return ' '.join(["-o", "BatchMode=yes",
                     "-o", "StrictHostKeyChecking=no",
                     "-o", "IdentityFile=%s" % key_filename,
                     "-o", "Port=%s" % port,
                     "-o", "ServerAliveCountMax=3",
                     "-o", "ServerAliveInterval=15",
                     "-o", "TCPKeepAlive=no",
                     ])

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
      raise SSHScriptFailedError(id=cmd_id, path=script, 
                                 hostname=params['hostname'], 
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
      raise SSHScriptFailedError(id=cmd_id, path=cmd, hostname=hostname, 
                                 errtxt=e.errtxt)

  def _local_execute(self, cmd, cmd_id, verbose=False, **kwargs):
    # Thanks to J.F. Sebastian from http://stackoverflow.com/questions/12270645/can-you-make-a-python-subprocess-output-stdout-and-stderr-as-usual-but-also-cap
    fout = StringIO()

    # execute script
    # using shell=True which gives better error messages for scripts lacking
    # an interpreter directive (i.e. #!/bin/bash) (?)
    exitcode = teed_call([cmd], stdout=fout, stderr=fout, verbose=verbose,
                         shell=True)

    # process results
    output = fout.getvalue()
    if exitcode:
      if not output: output = 'Error: exit code %s' % exitcode
      raise ScriptFailedError(id=cmd_id, path=cmd, errtxt=output)


def tee(infile, *files):
    """Print `infile` to `files` in a separate thread."""
    def fanout(infile, *files):
        for line in iter(infile.readline, ''):
            for f in files:
                if f: f.write(line)
        infile.close()
    t = Thread(target=fanout, args=(infile,)+files)
    t.daemon = True
    t.start()
    return t

def teed_call(cmd_args, **kwargs):    
    stdout, stderr, verbose = [kwargs.pop(s, None) for s in 
                               'stdout', 'stderr', 'verbose']
    p = Popen(cmd_args,
              stdout=PIPE if stdout is not None else None,
              stderr=PIPE if stderr is not None else None,
              **kwargs)
    threads = []
    if stdout is not None: threads.append(tee(p.stdout, stdout,
                                              sys.stdout if verbose else None))
    if stderr is not None: threads.append(tee(p.stderr, stderr, 
                                              sys.stderr if verbose else None))
    for t in threads: t.join() # wait for IO completion
    return p.wait()

#------ Errors ------#
class ScriptFailedError(DeployEventError):
  def __init__(self, id, path, errtxt):
    self.id = id
    self.path = path
    self.errtxt = errtxt

  def __str__(self):
    return "Error(s) occurred running '%s' script at '%s':\n\n%s" % (
            self.id, self.path, self.errtxt)

class SSHScriptFailedError(ScriptFailedError):
  def __init__(self, id, path, hostname, errtxt):
    self.id = id
    self.path = path
    self.hostname = hostname
    self.errtxt = errtxt

  def __str__(self):
    return ("Error(s) occurred running '%s' script at '%s' on '%s':\n\n"
            "%s" % (self.id, self.path, self.hostname, self.errtxt))
