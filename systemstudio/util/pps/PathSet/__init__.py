#
# Copyright (c) 2012
# System Studio Project. All rights reserved.
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
PathSet

PathSets are used as the return value for a few Path operations, such as
Path.findpaths() and Path.listdir()
"""

class PathSet(list):
  """
  A PathSet isn't a set in the strict sense; rather, it is a list of Path
  objects that defines a few extra functions for manipulation of the
  result.  PathSets are subclasses of list, so they can be used anywhere a
  list is expected; they also support the full compliment of normal list
  methods, like append(), extend(), list assignment, etc.
  """
  # standard list functions return PathSet instances instead of lists
  def __add__(self, other):
    return self.__class__(self + other)
  def __mul__(self, other):
    return self.__class__(self * other)
  def __getslice__(self, low, high):
    return self.__class__(list.__getslice__(self, low, high))

  def sort(self, type='name', reverse=False):
    """
    Sort the PathSet based on some property of the Paths it contains.
    Possible sort values include 'name' and any stat value of the
    underlying file the path refers to.  For example, setting type='size'
    means that the PathSet will be sorted on file size, while type='ino'
    will sort based on the underlying file's inode number.  Stat values
    are referenced by using their names in python's stat.py without the
    leading 'st_'; thus, 'st_atime' becomes 'atime', 'st_uid' becomes
    'uid', etc.  type can also be set to None; in this case, no sorting is
    performed.

    This is an in-place operation.  However, the method returns the
    PathSet it is operating on, which allows this method to be chained
    together with calls to other methods; for example,
    path.sort('atime').fnmatch('*.py').
    """
    if not type: return self

    # sort functions - returns a value by which sorting will be performed
    def sort_name(f, sorttype): return f
    def sort_stat(f, sorttype):
      try:
        sortval = eval('f.stat().st_%s' % sorttype)
      except AttributeError:
        raise ValueError("Invalid sort type '%s'" % sorttype)
      return sortval

    sortlist = []
    if type == 'name':
      sortfn = sort_name
    else:
      sortfn = sort_stat
      reverse = not reverse # file stat sorts are newer/larger first
    for f in self:
      sortval = sortfn(f, type)
      sortlist.append((sortval, f))

    sortlist.sort()
    if reverse: sortlist.reverse()

    del(self[:])
    self.extend([ f for _,f in sortlist ])
    return self

  def filter(self, pattern, invert=False):
    """
    In-place filter operation: removes files that match pattern; or, if
    inverted, removes all files that do not match pattern.  Like sort(),
    filter() also returns the PathSet it operates on, meaning it can be
    chained together with other PathSet methods in one line.
    """
    def match(path):
      res = path.fnmatch(pattern)
      if invert: return res
      else: return not res

    filtered = filter(match, self)
    del(self[:])
    self.extend(filtered)
    return self

  def fnmatch(self, pattern, invert=False):
    "In-place filter operation based on glob chars"
    def match(path):
      res = path.fnmatch(pattern)
      if not invert: return res
      else: return not res

    return self._filter(match)

  def rematch(self, pattern, invert=False):
    "In-place filter operation based on regular expressions"
    def match(path):
      res = path.rematch(pattern)
      if not invert: return res
      else: return not res

    return self._filter(match)

  def _filter(self, match):
    "Helper method for filter methods"
    filtered = filter(match, self)
    del(self[:])
    self.extend(filtered)
    return self

  def rm(self, **kwargs):
    "Call rm() on each path in the PathSet"
    for item in self:
      item.rm(**kwargs)

  def cp(self, dst, **kwargs):
    "Call cp() on each path in the PathSet"
    for item in self:
      item.cp(dst, **kwargs)

  def utime(self, times):
    "Call utime() on each path in the PathSet"
    for item in self:
      item.utime(times)

  def chmod(self, mode):
    "Call utime() on each path in the PathSet"
    for item in self:
      item.chmod(mode)

  def chown(self, uid, gid):
    "Call chown() on each path in the PathSet"
    for item in self:
      item.chown(uid, gid)

  def getsize(self):
    "Call getsize() on each path in the PathSet and return the sum"
    sum = 0
    for item in self:
      sum += item.lstat().st_size
    return sum

  def relpathfrom(self, path):
    "Call relpathfrom() on each path in the PathSet and return a new PathSet"
    return self.__class__([ x.relpathfrom(path) for x in self ])

  def relpathto(self, path):
    "Call relpathto() on each path in the PathSet and return a new PathSet"
    return self.__class__([ x.relpathto(path) for x in self ])
