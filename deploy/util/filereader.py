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
"""
filereader.py

A simple library for reading a file into a list, because dang its annoying to
rewrite the same code a million times over.
"""

import os
import shutil

from StringIO import StringIO

def read(file):
  """
  contentlist = read(file)

  Read a file into a list and return this list.  Newline characters are
  automatically stripped.
  """

  try:
    f = open(file)
  except (IOError, OSError), e:
    raise FileReaderError, str(e)

  ret = [ line.rstrip('\n') for line in f.readlines() ]
  f.close()

  return ret

def readFLO(flo, close=False):
  """
  contentlist = readFLO(flo[,close])

  'Read' a file-like object and return a list, as above in read().
  This does not close flo unless close is specified.
  """
  pos = flo.tell()
  ret = [ line.rstrip('\n') for line in flo.readlines() ]
  if close: flo.close()
  else:     flo.seek(pos)

  return ret


def write(list, file, newlines=True):
  """Write the contents of a list out to a file.  Newline characters are
  automatically added back in if newlines is true."""
  if not os.path.exists(file):
    try:
      os.mknod(file)
    except OSError, e:
      raise FileReaderError(str(e) + ': %s' % file)

  try:
    fdst = open(file, 'w')
  except OSError, e:
    raise FileReaderError(str(e))

  fsrc = __write(list, newlines)
  shutil.copyfileobj(fsrc, fdst)
  fsrc.close()
  fdst.close()

def writeFLO(list, newlines=True):
  "Write the contents of list to a file-like object, and return it"
  return __write(list, newlines)

def __write(lines, newlines=True):
  fsrc = StringIO()

  if not hasattr(lines, '__iter__'): lines = [lines]

  for line in lines:
    if newlines: fsrc.write(line + "\n")
    else:        fsrc.write(line)

  fsrc.seek(0)
  return fsrc


class FileReaderError(StandardError):
  """Class of errors raised when filereader encounters a problem; usually
  because the file in question doesn't exist"""
