#
# Copyright (c) 2007, 2008
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
locals.py

Locals data for systembuilder

This file contains a number of anaconda version-specific data for various
parts of the systembuilder process.  All information is stored in nested
LocalsDict objects.  See LocalsDict, below, for details on how it differs from
the standard dict object.
"""

import imp

from rendition import pps
from rendition import versort

# local data imports happen at bottom to avoid circular refs

__all__ = [] # populated automatically

class RemoveObject: pass

REMOVE = RemoveObject()

class LocalsDict(dict):
  """
  A LocalsDict is a subclass of dict with a specialized key lookup system
  that aids the specific requirements of the systembuilder locals system.

  Problem
  Certain properties of anaconda-based distributions vary depending on the
  anaconda version, such as image file location and format or discinfo file
  internal format.  While starting at a specific anaconda version, these
  particular properties may persist for a number of subsequent anaconda
  versions without changing.  In a traditional dictionary, encoding this
  would not only require a great deal of space, but would be very error prone,
  as any changes would have to potentially be applied to multiple places.

  Solution
  Instead of dictionary keys referring to a single point in anaconda's
  development cycle, a given key refers to all revisions from itself until
  the next highest key.  That is, in a LocalsDict with the keys '0', '1.5',
  and '4.0', any key request that sorts between '1.5' and '4.0' would return
  the value stored at '1.5'.  Thus, with this optimization, the developer
  need only create key, value pairs for anaconda versions where the relevant
  property in question changed in some way; all other versions can be ignored.

  LocalsDict uses versort for sorting of keys; as such, keys should consist
  of one or more integers separated by decimals ('.').  Sorting occurs exactly
  how one would logically expect rpm version numbers to sort (4.0 > 3.0.0,
  4.1 > 4.0.1, etc).  See versort.py for a full discussion of how indexes are
  sorted.

  Subsequent keys after the first provide updates to the values in previous
  keys; in the above example, then, the value returned by LocalsDict['4.0']
  would be the result of first updating LocalsDict['0'] with LocalsDict['1.5'],
  and then updating that result with LocalsDict['4.0'].  Updates are done
  recursively; that is, each level of the dictionary is updated, rather than
  just the topmost level.  In order to delete a given key, value pair, set
  a key's value to REMOVE.
  """
  def __getitem__(self, key):
    ret = {}
    for index in versort.sort(self.keys()):
      if index <= key:
        ret = rupdate(ret, dict.__getitem__(self, str(index)))
    return ret

def rupdate(dst, src):
  """
  Recursive dictionary updater.  Updates nested dictionaries at each level,
  rather than just at the top level.  Essentially, when calling a.update(b),
  we first check the contents of both a and b at each index i - if they are
  both dictionaries, then we call a[i].update(b[i]) instead of a[i] = b[i].
  """
  if not isinstance(src, dict):
    return src
  for k,v in src.items():
    if isinstance(v, dict):
      rdst = dst.setdefault(k, {})
      rupdate(rdst, v)
    elif v is REMOVE:
      if dst.has_key(k): del(dst[k])
    else:
      dst[k] = v
  return dst

def sort_keys(d, i='index'):
  "Sort they keys of a dictionary d based on the value of subdictionary keys i"
  return [ x for (x,y) in sorted(d.items(), _vcmp) ]

def _vcmp(a,b,i='index'):
  "Compare two key, value pairs based on the value of a[i] and b[i]"
  assert len(a) == 2, a
  assert len(b) == 2, b
  return _icmp(a[1], b[1], i)

def _icmp(a,b,i='index'):
  "Compare two dictionaries based on the value of a[i] and b[i]"
  assert a.has_key(i), a
  assert b.has_key(i), b
  return cmp(a[i],b[i])


# local data imports
for modfile in pps.path(__file__).dirname.listdir('*.py').filter('__init__.py'):
  modname = 'l_'+modfile.basename.splitext()[0]
  module = imp.load_source(modname, modfile)

  # add locals to global namespace
  for attr in module.__all__:
    globals()[attr] = getattr(module, attr)
    # add to __all__
    __all__.append(attr)
