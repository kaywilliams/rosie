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
import errno

from deploy.util.pps.lib import cached

from deploy.util.pps.PathStat import PathStat

from deploy.util.pps.Path import path_stat

from deploy.util.pps.Path.error import PathError, OfflinePathError

class CachedPath_Stat(path_stat.Path_Stat):
  """
  CachedPath objects save a cache of stat calls made to them due to the
  somewhat pricey cost of making stat calls.  There are two levels of
  caching: one on the Path object itself and one associated with this
  python module.  The goals for such a caching system are as follows:

   * all Path objects that have had stat() called on them contain a cached
     version of the result
   * a global cache of stat() calls allows recent stat() calls to be saved
     even when reference to the original Path object disappears (especially
     prevalent in walk() operations)
   * the global cache is limited in size as to prevent boundless growth

  The first two goals are accomplished.  The third is not; the cache is
  currenty boundless.  Several approaches have been made to resolve this,
  but all have been unsatisfactory due to very slow performance.  If you
  have a truly excessive number of stat results cached, you can clear it
  by calling path_stat.view.clear().
  """
  def exists(self):
    try:
      self.stat()
    except (PathError, OfflinePathError):
      return False
    return True

  def getatime(self): return self.stat().st_atime
  def getmtime(self): return self.stat().st_mtime
  def getctime(self): return self.stat().st_ctime
  def getsize(self):  return self.stat().st_size

  atime = property(getatime)
  mtime = property(getmtime)
  ctime = property(getctime)
  size  = property(getsize)

  def stat(self, populate=True):  return self._get_stat(populate=populate)
  def lstat(self, populate=True): return self._get_stat(populate=populate)

  # stat methods - outermost (earlier) caches are hit first
  @cached()
  @cached(globally=True)
  def _get_stat(self, populate=True):
    return self.mkstat(populate=populate)

  @cached(name='_get_stat', set=True)
  @cached(name='_get_stat', set=True, globally=True)
  def _set_stat(self, stat):
    estat = self._get_stat(populate=False)
    estat.update(*stat._stat)
    return estat

  def mkstat(self, populate=False):
    "return stats from cached file if available"
    if self.cache_handler and self.cache_handler.offline:
        csh = self.cache_handler.cshfile(self)
        if csh.exists():
          return csh._mkstat(populate=populate)
        else:
          raise OfflinePathError(self, 
                          strerror="operating in offline mode and "
                                   "file could not be found in the cache")
    else:
      return self._mkstat(populate=populate)

  _protect = ['_get_stat']
