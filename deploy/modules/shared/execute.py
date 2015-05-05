#
# Copyright (c) 2015
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

from deploy.dlogging import L2
from deploy.errors import DeployEventError
from deploy.util import pps
from deploy.util import shlib


__all__ = ['ExecuteEventMixin',
           'ScriptFailedError', 'SSHScriptFailedError',
           'LocalExecute', 'RemoteExecute']

class ExecuteEventMixin:
  execute_mixin_version = "1.00"

  def __init__(self):
    self.macros = getattr(self, 'macros', {})

  def setup(self, **kwargs):
    # this method need to be safe for calling by the main event and 
    # multiple mixins (e.g. DeployEventMixin, InputEventMixin)

    self.DATA['variables'].update(['execute_mixin_version', 'LOCAL_ROOT'])

    # for optimizing per-build directory cleaning/creation
    self.cvars.setdefault('visited-script-hosts', [])

    if not getattr(self, 'local_base', None):
      self.local_base = 'scripts/%s' % self.build_id

  def _local_execute(self, *args, **kwargs):
    if not hasattr(self, 'local_execute_obj'):
      self.local_execute_obj = LocalExecute(self)
    return self.local_execute_obj.execute(*args, **kwargs)

  def _remote_execute(self, *args, **kwargs):
    if not hasattr(self, 'remote_execute_obj'):
      self.remote_execute_obj = RemoteExecute(self)
    return self.remote_execute_obj.execute(*args, **kwargs)

class Execute:
  def __init__(self, ptr, local_root):
    self.ptr = ptr

    self.local_root = local_root

    self.datadir = local_root / self.ptr.local_base / 'data'
    self.scriptdir = local_root / self.ptr.local_base / 'scripts'

    # list of directories to be created
    self.dirlist = [ self.local_root ]                    # local root
    dir = self.local_root                                 # intermediate dirs
    for part in self.ptr.local_base.split('/'):
      dir = dir / part
      self.dirlist.append(dir)
    self.dirlist.extend([self.datadir, self.scriptdir]) # data and script dirs

  def execute(): # implemented by subclasses
    pass 

  def _execute(self, script, script_id, ssh=False, verbose=False):
    """Wrapper for shlib call that provides logging and error handling for
       scripts. If this is not wanted, make calls directly to shlib"""

    # always log script output when log level at 4 and below
    if self.ptr.logger.test(4):
      verbose = True

    # execute script
    try:
      output, errors, both = shlib.call(script, verbose=verbose, shell=True)
    except shlib.ShCalledProcessError, e:
      raise ScriptFailedError(script_id, script, e.returncode, e.both)

    # log error text if exist and error not raised
    if errors and not verbose:
      self.ptr.log(1, errors)

  def replace_macros(self, infile, outfile):
    text = infile.read_text()

    for macro, value in {'%{script-dir}': self.scriptdir,
                         '%{script-data-dir}': self.datadir}.items():
      text = text.replace(macro, value)

    outfile.write_text(text)


class LocalExecute(Execute):
  def __init__(self, ptr):
    Execute.__init__(self, ptr, local_root=ptr.LOCAL_ROOT)

  def execute(self, script, script_id, verbose=False):
    # make dirs as needed 
    if 'localhost' not in self.ptr.cvars['visited-script-hosts']:
      self.scriptdir.rm(recursive=True, force=True)
      for d in self.dirlist:
        d.exists() or d.mkdir(0700) and d.chown(0,0)
      self.ptr.cvars['visited-script-hosts'].append('localhost')

    # write script 
    tmpfile = self.scriptdir / script.basename 
    self.replace_macros(script,tmpfile)
    tmpfile.chmod(0700)
    tmpfile.chown(0,0)

    # execute script
    self._execute(tmpfile, script_id, verbose=verbose)

class RemoteExecute(Execute):
  def __init__(self, ptr):
    Execute.__init__(self, ptr, local_root=ptr.LOCAL_ROOT)

  def execute(self, script, script_id, params, verbose=False):
    # convenience variable
    hostname = params['hostname']

    # setup
    cmd = ''
    if hostname not in self.ptr.cvars['visited-script-hosts']:
      cmd += "rm -rf %s; " % self.scriptdir
      cmd += ("for d in %s; do "
              "[ -d \$d ] || mkdir -m 700 \$d && chown root:root \$d; "
              "done" % ' '.join(self.dirlist))
      self.ptr.cvars['visited-script-hosts'].append(hostname)
    if cmd:
      cmd = self._get_ssh_cmd(cmd, params)
      try:
        out, err, both = shlib.call(cmd, verbose=False, shell=True)
      except shlib.ShCalledProcessError, e:
        if "Host key verification failed" in e.both:
          raise HostKeyVerificationError(hostname, params['known_hosts_file'],
                                         getattr(self.ptr, 'ssh_host_key_file',
                                                 None),
                                         e.both)
        else:
          raise RemoteDirCreationError(cmd, hostname, e.returncode, e.both)

    # write script
    self.replace_macros(script, script)
    tmpfile = self.scriptdir / script.basename
    cmd = self._get_sftp_cmd("cd %s\nput %s ./\nchmod 700 %s" % 
                             (self.scriptdir, script, tmpfile), params)
    try:
      shlib.call(cmd, verbose=False, shell=True)
    except shlib.ShCalledProcessError, e:
      raise RemoteFileCreationError(cmd, hostname, e.returncode, e.both)
 
    # execute script
    self.ptr.log(4, L2("executing \'%s\' on host" % tmpfile))
    try:
      cmd = self._get_ssh_cmd(tmpfile, params)
      self._execute(cmd, script_id, ssh=True, verbose=verbose)
    except ScriptFailedError, e:
      raise SSHScriptFailedError(e.script_id, tmpfile, hostname, e.returncode,
                                 e.both)

  def _get_ssh_options(self, port, key_filename, known_hosts_file):
    return ' '.join(["-o", "BatchMode=yes",
                     "-o", "IdentityFile=%s" % key_filename,
                     "-o", "UserKnownHostsFile=%s" % known_hosts_file,
                     "-o", "Port=%s" % port,
                     "-o", "ServerAliveCountMax=3",
                     "-o", "ServerAliveInterval=15",
                     "-o", "TCPKeepAlive=no",
                     ])

  def _get_sftp_cmd(self, cmd, params):
    cmd = 'echo -e "%s" | /usr/bin/sftp -b - %s %s@%s' % (
          cmd, self._get_ssh_options(params['port'], params['key_filename'], 
                                     params['known_hosts_file']),
                                     params['username'], params['hostname'])
    return cmd

  def _get_ssh_cmd(self, cmd, params):
    cmd = '/usr/bin/ssh %s %s@%s "%s"' % (
          self._get_ssh_options(params['port'], params['key_filename'],
                                params['known_hosts_file']),
                                params['username'], params['hostname'], cmd)
    return cmd


#------ Errors ------#
class ScriptFailedError(DeployEventError):
  def __init__(self, script_id, path, returncode, both):
    self.script_id = script_id
    self.path = path
    self.returncode = returncode
    self.both = both

  def __str__(self):
    return ("Error(s) occurred running '%s' script at '%s':\n\n%s"
            % (self.script_id, self.path, self.both))

class SSHScriptFailedError(ScriptFailedError):
  def __init__(self, script_id, path, hostname, returncode, both):
    self.script_id = script_id
    self.path = path
    self.hostname = hostname
    self.returncode = returncode
    self.both = both

  def __str__(self):
    return ("Error(s) occurred running '%s' script at '%s' on '%s':\n\n"
            "exit code: %s\n\n%s" %
            (self.script_id, self.path, self.hostname, self.returncode,
             self.both))

class HostKeyVerificationError(DeployEventError):
  def __init__(self, hostname, known_hosts_file, managed_file, both):
    self.hostname = hostname
    self.known_hosts_file = known_hosts_file
    self.both = both
    self.managed_file = managed_file

    self.message = ("Unable to verify host '%s' using the known hosts "
                    "file at '%s':\n\n"
                    "%s"
                    % (self.hostname, self.known_hosts_file, self.both))

    if self.known_hosts_file == self.managed_file:
      self.message += ("\nIf a change in the client public key is expected, "
                       "delete the file at '%s' and try again."
                       % self.known_hosts_file)

  def __str__(self):
    return self.message

class RemoteFileError(DeployEventError):
  def __init__(self, cmd, hostname, returncode, both):
    self.cmd = cmd
    self.hostname = hostname
    self.returncode = returncode
    self.both = both

class RemoteDirCreationError(RemoteFileError):
  def __init__(self, *args, **kwargs):
    RemoteFileError.__init__(self, *args, **kwargs)

  def __str__(self): # note - keep this in sync with RemoteFileCreationError
    return ("Error creating script directories on '%s':\n\n"
            "command: %s\n\n"
            "exit code: %s\n\n"
            "command output:\n%s" %
            (self.hostname, self.cmd, self.returncode, self.both))

class RemoteFileCreationError(RemoteFileError):
  def __init__(self, *args, **kwargs):
    RemoteFileError.__init__(self, *args, **kwargs)

  def __str__(self): # note - keep this in sync with RemoteDirCreationError
    return ("Error copying script to '%s':\n\n"
            "command: %s\n\n"
            "exit code: %s\n\n"
            "command output:\n%s" %
            (self.hostname, self.cmd, self.returncode, self.both))
