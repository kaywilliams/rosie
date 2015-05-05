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
"""
shlib.py

Convenience utilities for executing shell functions

Thanks to J.F. Sebastian from
http://stackoverflow.com/questions/12270645/can-you-make-a-python-subprocess-output-stdout-and-stderr-as-usual-but-also-cap
(Note - this works quite well, but still we have seen cases where the order of
stdout and stderr messages is not always as expected, and results differ across
systems)
"""

import sys

from StringIO import StringIO
from subprocess import Popen, PIPE, CalledProcessError
from threading  import Thread

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
    stdout, stderr = [kwargs.pop(s, None) for s in 'stdout', 'stderr']
    outlist, errlist = [kwargs.pop(s, []) for s in 'outlist', 'errlist']

    if stdout: outlist.append(stdout)
    if stderr: errlist.append(stderr)

    p = Popen(cmd_args,
              stdout=PIPE if outlist else None,
              stderr=PIPE if errlist else None,
              **kwargs)
    threads = []
    if outlist is not None: threads.append(tee(p.stdout, *outlist)) 
    if errlist is not None: threads.append(tee(p.stderr, *errlist)) 
    for t in threads: t.join() # wait for IO completion
    return p.wait()

def call(cmd_args, **kwargs):
  """
  Similar to subprocess check_call and check_output methods, with added support
  for display and capture of stdout and stderr. Supports these additional
  attributes:

  * verbose -         Controls whether output and errors are sent to the
                      standard streams. Defaults to True.

  Waits for the command to complete. If the return code was zero, returns a
  tuple of four objects:

  * returncode - exit code from the process
  * output - text captured from the standard output stream
  * errors - text captured from the standard error stream
  * both - interleaved output and error text

  If the return returncode was non-zero, raises a ShCalledProcessError, with
  the attributes 'output', 'errors', and 'both'.
  """

  verbose = kwargs.pop('verbose', True)

  # create file objects
  fout = StringIO()  # for capturing output text
  ferr = StringIO()  # for capturing error text
  fboth = StringIO() # for capturing interspersed output and errors

  outlist = [ fout, fboth, sys.stdout if verbose else None ]
  errlist = [ fout, fboth, sys.stderr if verbose else None ]
  
  returncode = teed_call(cmd_args, outlist=outlist, errlist=errlist, **kwargs)

  output = fout.getvalue()
  errors = ferr.getvalue()
  both = fboth.getvalue()

  if returncode != 0:
    raise ShCalledProcessError(cmd_args, returncode, output, errors, both)

  return output, errors, both

def execute(cmd, verbose=False):
  """
  Execute cmd, displaying output if verbose is true.  Raises a ShExecError
  if cmd returns a nonzero status code.  Otherwise, returns all the lines in
  stdout in a list. Similar to subprocess.check_output() in Python 2.7.
  """

  proc = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
               close_fds=True)

  stdout, stderr = proc.communicate()

  if stdout:
    stdout = stdout.rstrip().split('\n')
  else:
    stdout = []

  status = proc.returncode

  if status != 0:
    errstr = "Error code: %s\n" % status
    errstr += stderr
    raise ShExecError(status >> 8, status, errstr, cmd)

  if stderr: stdout.append(stderr)

  if verbose:
    for line in stdout: print line

  return stdout

class ShCalledProcessError(StandardError):
  def __init__(self, cmd, returncode, output, errors, both, message=None):
    self.returncode = returncode
    self.output = output
    self.errors = errors
    self.both = both
    self.message = message or (
      "Command '%s' returned non-zero exit status '%s'" % (cmd, returncode))

  def __str__(self):
    return self.message

class ShExecError(StandardError):
  "Class of errors raised when shlib encouters an error in program execution"
  def __init__(self, errno, retcode, desc, cmd):
    self.errno = errno
    self.retcode = retcode
    self.desc  = desc
    self.cmd   = cmd

  def __str__(self):
    return self.desc
