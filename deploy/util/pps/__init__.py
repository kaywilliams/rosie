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
PPS - Python Pathing System (boring name, will be more creative later!)

A common interface for file paths at any accessible location, both local
and remote. The PPS provides a means for manipulating files across a
variety of protocols in a consistent manner.  Furthermore, it provides a
number of convenient methods on path objects that are ordinarily scattered
across the standard library.  Finally, it is fully extensible; a file in
any location that can implement the interface can be used completely
interchangeably with any other path.

File paths are categorized by their 'protocol', which is the method by
which a computer operating system reads and writes to them.  The protocol
for file access is often contained in the path itself (for example, 'http'
in 'http://www.example.com' or 'ftp' in 'ftp://redhat.com'), but is
sometimes omitted if it can be implied or if the path refers to a local
file.  Each protocol can have its own, separate implementation of the pps
Path interface.  Not all protocols have complete support for all the
features exposed in the interface; partial implementations will result in
support for a subset of the features of pps Path objects.

The PPS system also defines a few helper classes that Path objects use in
their normal operation.  A PathSet is a list of Path objects, with a few
extra methods for sorting and filtering results.  PathStat objects are a
representation of the result of a stat() call on a given path.  PathToken
objects are a tokenized version of Path objects that provide an alternate
indexing method.  See the modules themselves for more information on the
purpose and function of these classes.
"""

def path(string, *args, **kwargs):
  """Factory function to create a Path object of the correct type from a
  string.  NOTE - if you want to create a (local) path without a scheme that
  contains ':', use pps.Path.local.path() instead.
  """
  if isinstance(string, Path.BasePath):
    return string
  elif string is None:
    return None

  return _path(string, *args, **kwargs)

def _path(string, *args, **kwargs):
  i = string.find(':')
  if i > 0:
    scheme = string[:i].lower()
  else:
    scheme = None # for local paths

  if scheme not in registered_schemes:
    scheme = None # assume its a local path

  fn, fargs, fkwargs = registered_schemes[scheme]
  args = list(args)
  args.extend(fargs)
  kwargs.update(fkwargs)

  return fn(string, *args, **kwargs)

registered_schemes = {}
def register_scheme(scheme, fn, args=None, kwargs=None):
  "Register a given scheme with a factory function to create a path of "
  "that type.  Optionally passes *args, and **kwargs to fn"
  registered_schemes[scheme] = (fn, args or [], kwargs or {})

# by waiting to import until after the register_scheme function, we allow path
# modules to import it without creating a circular dependency
#
# path modules should avoid making a local copy of the path function as this 
# obstructs function wrapping by the cache and search_paths handlers, 
# specifically,
#
# do this:
#
#   import deploy.util
#   p = deploy.util.pps.path('somepath')
# 
# rather than this:
#
#   from deploy.util.pps import path
#   p = path('somepath')
#

import Path

#import Path.ftp # not fully implemented
import Path.mirror
import Path.http
import Path.local
