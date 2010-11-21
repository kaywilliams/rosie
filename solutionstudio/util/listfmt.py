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
listfmt.py

A list formatter

Prints out a list, applying a format to it.  The following format elements
are available:

 <pre>     : prepended before every list item
 <post>    : affixed after every list item
 <sep>     : seperator between list items
 <start>   : inserted before all list items
 <end>     : appended after all list items
 <last>    : inserted before final list item

For example, <pre>='"', <post>='"', sep=', ', start='List: ', end='.',
last='and ' applied to the list [1,2,3,4,5] would result in:

List: "1", "2", "3", "4", and "5".

as output.
"""

def format(iterable, pre=None, post=None, sep=None,
                     start=None, end=None, last=None):
  if len(iterable) > 0:

    fmt = dict(pre=pre or '', post=post or '', sep=sep or '',
               start=start or '', end=end or '', last=last or sep or '')


    # construct a big string wtih all the formats in place and $items
    s = '%(start)s$item'
    for i in range(0, len(iterable)-2):
      s += '%(sep)s$item'
    if len(iterable) < 2:
      s += '%(end)s'
    else:
      s += '%(last)s$item%(end)s'

    # replace the $items with elements from the iterable
    for i in iterable:
      s = s.replace('$item', '%%(pre)s%s%%(post)s' % i, 1)

    return s % fmt
  else:
   return ''

def pprint(list):
  return format(list, sep=', ', last='and ')

class ListFormatter(object):
  "A class for doing the same kind of formatting to a number of lists"
  def __init__(self, pre=None, post=None, sep=None,
                     start=None, end=None, last=None):
    self.pre   = pre
    self.post  = post
    self.sep   = sep
    self.start = start
    self.end   = end
    self.last  = last

  def format(self, list):
   return format(list, **self.__dict__)
