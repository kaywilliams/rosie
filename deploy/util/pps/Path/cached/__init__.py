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

from copy import copy

import deploy.util

from deploy.util.pps.UriTuple import urlunparse

from deploy.util.pps.Path import BasePath

from path_io   import CachedPath_IO
from path_stat import CachedPath_Stat

from deploy.util.pps.Path import Path_Printf as CachedPath_Printf
from deploy.util.pps.Path import Path_Walk   as CachedPath_Walk

class _CachedPath(BasePath):
  """
  String representation of cached file paths. Provides support for a 
  for a cache_handler, which is used for performing stat and io operations 
  against a cached copy of the file. 
  """
  def __new__(cls, value, **kwargs):
    return BasePath.__new__(cls, value)

  def __init__(self, value, cache_handler=None, **kwargs):
    self.cache_handler = cache_handler

  def _new(self, string):
    return deploy.util.pps.path(string)


class CachedPath(CachedPath_IO, CachedPath_Printf, CachedPath_Stat,
                 CachedPath_Walk, _CachedPath):
  pass
