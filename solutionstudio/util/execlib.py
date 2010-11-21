#
# Copyright (c) 2010
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
"""
shlib 2.0
"""

import os
import sys
import fcntl
import shlex

_stdfds = ['stdin', 'stdout', 'stderr']
_fdmodes = {'stdin': 'w', 'stdout': 'r', 'stderr': 'r'}

class Executable:
  def __init__(self, path):
    self.binary = path

  def run(self, args, stdin=None, stdout=None, stderr=None):
    proc = Process()

    self._mkpipe(proc, 'stdin',  fd=stdin)
    self._mkpipe(proc, 'stdout', fd=stdout)
    self._mkpipe(proc, 'stderr', fd=stderr)

    if isinstance(args, str):
      args = shlex.split(args)

    proc.pid = os.fork()
    if proc.pid == 0: self._as_child(proc, args)
    return self._as_parent(proc)

  def _mkpipe(self, proc, fdname, fd=None):
    # makes pipes and add to proc
    if fd is None:
      pipe = os.pipe()
      if _fdmodes[fdname] == 'w': pipe = (pipe[1], pipe[0])
      proc._pipes[fdname] = Pipe(pipe[0], pipe[1], 0)
    else:
      proc._pipes[fdname] = Pipe(fd.fileno(), fd.fileno(), 1)

  def _as_parent(self, proc):
    # close pipes
    for k,v in proc._pipes.items():
      if not v.keepopen:
        os.close(v.child)
        proc.handles[k] = os.fdopen(v.parent, _fdmodes[k])

    #del proc._pipes

    return proc

  def _as_child(self, proc, args):
    # dupliate attached stdin, stdout, stderr to 'normal' ones
    for fd in _stdfds:
      p = proc._pipes[fd]
      os.dup2(p.child, getattr(sys, '__%s__' % fd).fileno())

    # close file descriptors
    for k,v in proc._pipes.items():
      if not v.keepopen:
        os.close(v.parent)

    # execute command
    cmd = [ self.binary ] + args
    os.execvp(cmd[0], cmd)

class Pipe:
  def __init__(self, parent, child, keepopen):
    self.parent = parent
    self.child  = child
    self.keepopen = keepopen

class Process:
  def __init__(self):
    self._pipes = {}
    self.handles = {}
    self.pid = None

  # the following are only available if run() isn't passed that specific argument;
  # for example, if stderr is specified, then stderr() raises an exception
  def stdout(self): return self.handles['stdout']
  def stderr(self): return self.handles['stderr']
  def stdin(self):  return self.handles['stdin']

  def wait(self):
    e = os.waitpid(self.pid, 0)[1]
    if e != 0:
      try:
        errstr = self.stderr().readlines()
      except IndexError:
        errstr = None
      raise ExecuteError(e >> 8, errstr)


def execute(cmdstr):
  cmd, args = cmdstr.split(None, 1)
  x = Executable(cmd)
  proc = x.run(args)

  stdout = [ l.rstrip('\n') for l in proc.stdout().readlines() ]
  stderr = [ l.rstrip('\n') for l in proc.stderr().readlines() ]

  try:
    proc.wait()
  except ExecuteError, e:
    errstr = ''
    for line in stderr: errstr += line + '\n'
    raise ExecuteError(e.errno, errstr)

  return stdout


class ExecuteError(StandardError):
  def __init__(self, errno, desc=''):
    self.args = (errno, desc)
    self.errno = errno
    self.desc = desc
