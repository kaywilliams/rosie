#
# Copyright (c) 2011
# OpenProvision, Inc. All rights reserved.
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
magic.py

Magic number comparisons - verify that a file at least claims to be the
type that we expect it to be.

A 'magic number' is a sequence of two or more bytes somewhere in a file that
can be used to identify the type of the file.  In many files, these are the
first few bytes of the file; an example is the 'shebang' syntax in shell
scripts.  By reading these bits and comparing them to a list of expected
values, we can attempt to determine the type of a file.
"""

__author__  = "Daniel Musgrave <dmusgrave@openprovision.com>"
__version__ = "1.0"
__date__    = "April 17th, 2007"

import struct

# import pps, if available
try:
  from openprovision.util import pps
except ImportError:
  pps = None

#------ CONSTANTS ------#
TYPE_STRING = 's'
TYPE_SHORT  = 'H'
TYPE_LONG   = 'L'

ENDIAN_LITTLE = '<'
ENDIAN_BIG    = '>'

LENGTH_SHORT = 2
LENGTH_LONG  = 4

#------ FILE TYPES ------#
# these values are returned by match(), below
FILE_TYPE_BZIP2    = 'application/x-bzip'
FILE_TYPE_GZIP     = 'application/x-gzip'
FILE_TYPE_SQUASHFS = 'application/x-squashfs'
FILE_TYPE_EXT2FS   = 'application/x-linux-ext2fs'
FILE_TYPE_CPIO     = 'application/x-cpio'
FILE_TYPE_GPGKEY   = 'application/x-gpg-key'
FILE_TYPE_LSS      = 'Syslinux SLL16 image data'
FILE_TYPE_FAT      = 'FAT filesystem'
FILE_TYPE_JPG      = 'JPEG image data'
FILE_TYPE_PNG      = 'PNG image data'
FILE_TYPE_DIR      = 'directory'
FILE_TYPE_EMPTY    = 'empty'

#------ MAGIC NUMBERS ------#
# Dictionary of known magic numbers. Keys are from the list of file types,
# above.  Each element is a list of magic number tuples, which have the
# following format:
#  * offset - the location of the magic number in the file, in bytes
#  * type   - the data type of the magic number
#  * endian - the 'endianness' of the magic number
#  * value  - the expected value of the magic number
# The list is intentionally kept down to only the numbers we (currently)
# care about.  As a more general solution, this list could easily be expanded
# upon.
magic = {
  # (offset, type, endianness, value)
  FILE_TYPE_BZIP2:    [(0,    TYPE_STRING, ENDIAN_BIG,    'BZh')],
  FILE_TYPE_GZIP:     [(0,    TYPE_STRING, ENDIAN_BIG,    '\x1f\x8b\x08')],
  FILE_TYPE_SQUASHFS: [(0,    TYPE_STRING, ENDIAN_BIG,    'hsqs')],
  FILE_TYPE_EXT2FS:   [(1080, TYPE_SHORT,  ENDIAN_LITTLE, 61267L)], # 0xEF53
  FILE_TYPE_CPIO:     [(0,    TYPE_SHORT,  ENDIAN_BIG,    70707L),
                       (0,    TYPE_STRING, ENDIAN_BIG,    '070701'),
                       (0,    TYPE_STRING, ENDIAN_BIG,    '070702'),
                       (0,    TYPE_STRING, ENDIAN_BIG,    '070707')],
  FILE_TYPE_GPGKEY:   [(0,    TYPE_STRING, ENDIAN_BIG,    '-----BEGIN PGP')],
  FILE_TYPE_LSS:      [(0,    TYPE_LONG,   ENDIAN_LITTLE, 0x1413f33d)],
  FILE_TYPE_FAT:      [(510,  TYPE_SHORT,  ENDIAN_LITTLE, 43605L)], # 0xAA55
  FILE_TYPE_JPG:      [(0,    TYPE_SHORT,  ENDIAN_BIG,    0xffd8)],
  FILE_TYPE_PNG:      [(0,    TYPE_STRING, ENDIAN_BIG,    '\x89PNG'),],
}


class MagicNumber:
  "A class representing a magic number"
  def __init__(self, desc, offset, type, endian, value):
    self.desc = desc
    self.offset = offset
    self.type = type
    self.endian = endian
    self.value = value

  def __str__(self): return self.desc

  def match(self, data):
    """Match data against the magic number defined by this class.  Return True
    if data matches, False otherwise."""
    try:
      if   self.type == TYPE_STRING: return self._string_match(data)
      elif self.type == TYPE_SHORT:  return self._short_match(data)
      elif self.type == TYPE_LONG:   return self._long_match(data)
      else: return None
    except struct.error:
      return None

  #------ MATCH HELPER FUNCTIONS ------#
  def _string_match(self, data):
    c = ''; s = ''
    for i in range(0, len(self.value)+1):
      if i + self.offset > len(data) - 1: break
      s = s + c
      [c] = struct.unpack('c', data[self.offset + i])
    return self.value == s

  def _short_match(self, data):
    [data] = struct.unpack(self.endian + self.type,
                           data[self.offset : self.offset+LENGTH_SHORT])
    return self.value == data

  def _long_match(self, data):
    [data] = struct.unpack(self.endian + self.type,
                           data[self.offset : self.offset+LENGTH_LONG])
    return self.value == data

def match(file, size=2048):
  "Attempt to match a file to one of the known magic numbers."
  try:
    if pps:
      data = pps.path(file).read_text(size)
    else:
      data = open(file).read(size)
  except IOError, e:
    if e.errno == 21:
      return FILE_TYPE_DIR
    else:
      raise
  if not data:
    return FILE_TYPE_EMPTY
  for test in MAGIC_NUMBERS:
    if test.match(data):
      return test.desc
  return None

# set up a global list of known magic numbers from the magic dict, above
MAGIC_NUMBERS = []
for k,v in magic.items():
  for m in v:
    MAGIC_NUMBERS.append(MagicNumber(k, *m))

if __name__ == '__main__':
  import sys
  if len(sys.argv) != 2:
    print 'usage: magic.py FILE'
    sys.exit(2)
  print match(sys.argv[1])
