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

import errno

import deploy.util

from deploy.util.pps.lib import file_cache

from deploy.util.pps.Path import Path_IO
from deploy.util.pps.Path.error import PathError

class CachedPath_IO(Path_IO):
  def link(self, dst):
    self.cp(dst, link=True)

  def _copy(self, dst, force=False, **kwargs):
    if (not self.cache_handler or self.islink() 
                               or dst.dirname == self.cache_handler.cache_dir):
      return Path_IO._copy(self, dst, **kwargs)

    else: # cache
      csh=self.cache_handler.cshfile(self)
      self._cached_copy(csh=csh, dst=dst, force=force, io_obj=Path_IO, **kwargs)

  @file_cache()
  def _cached_copy(self, **kwargs):
    csh = kwargs.pop('csh')
    dst = kwargs.pop('dst')
    callback = kwargs.pop('callback', None)

    if callback and hasattr(callback, '_notify_copy'):
      callback._notify_copy()
    csh._copy(dst=deploy.util.pps.path(dst), callback=callback, **kwargs)

  def open(self, mode='r', seek=None, **kwargs):
    if not self.cache_handler:
      return self._open(mode=mode, seek=seek, **kwargs)

    csh = self.cache_handler.cshfile(self)

    if self.cache_handler.offline:
      return csh._open(mode=mode, seek=seek, **kwargs)
                                       
    else:
      return self._cached_open(csh=csh, io_obj=Path_IO, mode=mode, 
                               seek=seek, **kwargs)

  @file_cache()
  def _cached_open(self, **kwargs):
    try:
      return kwargs['csh']._open(**kwargs)
    except PathError, e:
      raise PathError(e.errno, self, 
                      strerror="error opening file from cache")

  _protect = ['open']

