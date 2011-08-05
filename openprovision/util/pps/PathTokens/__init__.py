#
# Copyright (c) 2011
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
PathTokens - an alternate representation of Path objects
"""

from openprovision.util.pps import path

class PathTokens(list):
  """
  PathTokens allows a path to be indexed as a list with [] operations where the
  indicies refer to directories in the path, rather than characters in the path
  string.  Both getting and slicing are supported.  For example,

   >>> p = PathTokens('/var/www/html/open_software')
   >>> p[1]
   var
   >>> p[0:3]
   /var/www
   >>> p[-2:]
   html/open_software

  PathTokens[0] of an absolute path returns the absolute root, whether it be
  '/' for file paths or '<protocol>://<realm>/' for other path types.

  PathTokens get and slice operations return objects of the same base class as
  the original path.  So, if a PathTokens object was created on a FilePath
  object, any get or slice will also return a FilePath object.
  """

  def __init__(self, iterable):
    if not hasattr(iterable, '__iter__'):
      iterable = path(iterable).splitall()

    list.__init__(self, iterable)

  def __getslice__(self, low, high):
    items = list.__getslice__(self, low, high)
    if not items: return None
    return items[0].__class__(items[0]._pypath.join(*items))
  def __str__(self):
    return str.__str__(self.__getslice__(0, len(self)))
  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__,
                       list.__getslice__(self, 0, len(self)))
  def __iter__(self):
    # note list.__getslice__ not self.__getslice__ (former treats self as a
    # list of directories; latter treats self as a string)
    return iter(list.__getslice__(self, 0, len(self)))
