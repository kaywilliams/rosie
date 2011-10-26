#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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
SeqLib.py

Library for parsing input strings and returning a list of integers in a sequence

Input strings consist of one or more tokens which are parsed and returned in a
simple list.  This library may or may not be of actual use; it was originally
based on the bash version of seqlib, where it served a much more useful purpose.
"""

__author__  = "Daniel Musgrave <dmusgrave@centosstudio.org>"
__version__ = "1.0"
__date__    = "17 November 2006"
__credits__ = "Me, because I'm so awesome"

import re

def convert(string):
  """Converts input string into a list of integers

     Input string should be a list of comma-separated tokens.  A token is any one
     of the following:
       * any positive integer (1, 3, 25, etc)
       * a range of positive integers (1-5, 25-1000, 41-25, etc). The range need
         not be ascending.
       * one of the keywords 'BEGIN' or 'END'
     convert() returns a list of integers as computed from this sequencing

     Example: convert("5,6,10-13") returns [5,6,10,11,12,13]"""

  keywords = ["BEGIN", "END"]

  sequence = []

  tokenIndex = 0
  for token in string.split(','):
    # integer token handler ('5', '26', etc)
    intToken = re.compile("^[0-9]+$").match(token)
    if intToken:
      sequence.append(int(intToken.group()))
      continue
    # range token handler ('6-8', '100-55', etc)
    rangeToken = re.compile("^[0-9]+-[0-9]+$").match(token)
    if rangeToken:
      sub = re.compile("[0-9]+").findall(rangeToken.group())
      if sub and len(sub) >= 2:
        rangeStart = eval(sub[0])
        rangeEnd = eval(sub[1])
        if rangeStart < rangeEnd:
          sequence.extend(range(rangeStart, rangeEnd + 1))
        else:
          sequence.extend(range(rangeStart, rangeEnd - 1, -1))
        continue
    if token in keywords:
      sequence.append(token)
      continue

    # if we havent been handled yet, token is invalid
    #raise InvalidToken(token, tokenIndex)
    raise ValueError("Invalid token \"" + str(token) + "\" at " + str(tokenIndex))

  return sequence
