#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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
# si.py
#
# simple tools for parsing si-style strings into their equivalent integer size

__author__  = 'Daniel Musgrave <dmusgrave@repostudio.org>'
__version__ = '1.0'
__date__    = 'January 14th, 2007'

import re

SIZE_REGEX = re.compile(
  '[\s]*'
  '([\d]+(?:\.[\d]+)?)' # decimal
  '[\s]*'
  '([KMGTPE]?)' # ordinal, optional
  '([I]?)'      # si: 'i', metric: ''
  '[B]?'        # bytes indicator, optional
  '[\s]*$',
  flags=re.IGNORECASE,
)

ORDINALS = ['', 'K', 'M', 'G', 'T', 'P', 'E']

def parse(s):
  """
  Parse a string possibly ending with one or more ordinals and an optional
  'b' character.  Returns an integer representing the number of bytes this
  string refers to.

  If the string s contains an 'i' after the ordinal, then the si standard
  of 1024 bytes per KiB is used, as defined by IEC1998; otherwise, 1000 bytes
  per KB is used.

  For user convenience, case and whitespace insensitve; for example, the
  following are all equivalent:
    1k   1kb   1 k   1 kb
    1K   1Kb   1 K   1 Kb
  """
  if isinstance(s, int) or isinstance(s, float):
    r = s
  elif isinstance(s, str):
    q = s.upper()
    try:
      n, ord, std = SIZE_REGEX.match(q).groups() # raises AttributeError if no matches
    except AttributeError, e:
      raise ValueError('Unable to parse size from string \'%s\'' % s)
    n = float(n)
    ord = ord.upper()
    if std: m = 1024
    else:   m = 1000
    try:
      r = n * (m**ORDINALS.index(ord)) # raises ValueError if not found
    except ValueError, e:
      # this will technically never be reached due to the RE that I use
      raise ValueError('Invalid ordinal \'%s\'' % ord)
  else:
    raise TypeError()

  return int(round(r))
