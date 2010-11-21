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
PathStat

A python representation of a stat() call on a Path object.  This file merely
defines the interface; see the individual modules for specific implementation.
"""

import itertools
import stat

from solutionstudio.util.pps.constants import *

N_STAT_ITEMS = 10
DEFAULT_STAT_ORDER = ['st_mode', 'st_ino',  'st_dev',   'st_nlink', 'st_uid',
                      'st_gid',  'st_size', 'st_atime', 'st_mtime', 'st_ctime']

class PathStat:
  STAT_ORDER = DEFAULT_STAT_ORDER

  def __init__(self, path, **kwargs):
    """
    PathStats appear to be a subclass of tuple; however, unlike tuples, they
    are (somewhat) mutable in order to allow them to be partially updated when
    necessary.  They are similar to the stat results returned by os.stat();
    however, they are implemented fully in python.

    Attributes can be accessed either via their indices (which correspond
    directly to those defined in python's stat module) or by their name.  For
    example, the st_mtime attribute of a PathStat object returns the modified
    time of the file the PathStat represents.

    Because computing the stat results can be an expensive operation, it is
    lazy, meaning that stat values are undefined until they are accessed
    directly.  PathStat objects avoid calling stat() until they absolutely
    have to, meaning that if the object is instantiated with one or more
    fields populated and none of the undefined fields are ever accessed, the
    PathStat object will never call stat().  This allows some operations,
    such as walk() in HttpPath objects, to procede much more quickly than
    they ordinarily would.

    See .update() for accepted kwargs.
    """
    self.uri = path
    self._stat = list(itertools.repeat(None, N_STAT_ITEMS))

    # set stat values
    self.update(**kwargs)

  # these methods make PathStat objects appear to be tuples
  def __repr__(self): return '%s(%s)' % (self.__class__.__name__, self.__str__())
  def __str__(self):  return str(tuple(self._stat))

  def __getitem__(self, key):
    "'Lazy' get; only calls stat() when the field in question is None"
    item = self._stat[key]
    if item is None:
      self.stat()
    else:
      return item
    return self._stat[key]

  def stat(self):
    """
    PathStat modules need to implement just this method.  It should compute
    and set the values of all 10 stat fields when called.
    """
    raise NotImplementedError

  def update(self, st_mode=None,  st_ino=None,   st_dev=None,  st_nlink=None,
                   st_uid=None,   st_gid=None,   st_size=None, st_atime=None,
                   st_mtime=None, st_ctime=None):
    """
    Allows updates to be performed on the various path fields.  This can be
    used to save time in the event that calling .stat() is expensive.  Ignores
    keys that are invalid (does not raise an exception).  Changing the file
    type is handled by using 'type' as the argument; other fields are accessed
    using their stat names ('st_*').
    """

    # update stat values
    for sid in self.STAT_ORDER:
      key = eval('stat.%s' % sid.upper())
      val = eval(sid)
      # if no val has been set, skip updating it
      if val is None: continue
      else: val = int(val)

      # unconditonally update if stat value has yet to be set
      if self._stat[key] is None:
        self._stat[key] = val
      # only update existing stat values if val is not -1
      else:
        if val != -1:
          self._stat[key] = val

  # attribute setup - all attributes are read-only
  st_atime = property(lambda self: self[stat.ST_ATIME])
  st_ctime = property(lambda self: self[stat.ST_CTIME])
  st_dev   = property(lambda self: self[stat.ST_DEV])
  st_gid   = property(lambda self: self[stat.ST_GID])
  st_ino   = property(lambda self: self[stat.ST_INO])
  st_mode  = property(lambda self: self[stat.ST_MODE])
  st_mtime = property(lambda self: self[stat.ST_MTIME])
  st_size  = property(lambda self: self[stat.ST_SIZE])
  st_uid   = property(lambda self: self[stat.ST_UID])
