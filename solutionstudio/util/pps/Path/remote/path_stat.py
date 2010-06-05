#
# Copyright (c) 2010
# Solution Studio. All rights reserved.
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
from solutionstudio.util.pps.lib import cached

from solutionstudio.util.pps.PathStat import PathStat

from solutionstudio.util.pps.Path import path_stat

class RemotePath_Stat(path_stat.Path_Stat):
  """
  RemotePath objects save a cache of stat calls made to them due to the
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
    return self._mkstat(populate=populate)

  @cached(name='_get_stat', set=True)
  @cached(name='_get_stat', set=True, globally=True)
  def _set_stat(self, stat):
    estat = self._get_stat(populate=False)
    estat.update(*stat._stat)
    return estat

  def _mkstat(self, populate=False):
    stat = PathStat(self)
    if populate: stat.stat()
    return stat

  _protect = ['_get_stat']
