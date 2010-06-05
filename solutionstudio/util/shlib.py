#
# Copyright (c) 2010
# Solution Studio. All rights reserved.
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

A basic library for executing shell functions, because the default python
ones are cumbersome!
"""

import popen2

def execute(cmd, verbose=False):
  """Execute cmd, displaying output if verbose is true.  Raises a ShExecError
  if cmd returns a nonzero status code.  Otherwise, returns all the lines in
  stdout in a list.
  """

  proc = popen2.Popen3(cmd, True)
  status = proc.wait()

  stdout = [ line.rstrip("\n") for line in proc.fromchild.readlines() ]
  proc.fromchild.close()
  stderr = [ line.rstrip("\n") for line in proc.childerr.readlines() ]
  proc.childerr.close()

  if status != 0:
    errstr = "Error code: %s\n" % status
    for line in stderr: errstr += line + "\n"
    raise ShExecError(status >> 8, errstr, cmd)

  if verbose:
    for line in stdout: print line

  return stdout


class ShExecError(StandardError):
  "Class of errors raised when shlib encouters an error in program execution"
  def __init__(self, errno, desc, cmd):
    self.errno = errno
    self.desc  = desc
    self.cmd   = cmd

  def __str__(self):
    return self.desc
