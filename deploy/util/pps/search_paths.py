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
"""
search_paths.py - a handler for setting default search_paths for use during
pps path initialization.
"""

from functools import wraps

import deploy.util

from deploy.util.pps import path as _orig_path

class SearchPathsHandler(object):
  """
  A handler that wraps the deploy.util.pps.path method to provide a default
  search_paths attribute.

  SearchPathHandlers have a single attribute:
   * search_paths:  Dictionary of search paths passed to the
                    deploy.util.pps.path method. See the deploy.util.pps.path
                    method for more information on the search_paths attribute.

  SearchPathHandler instances wrap (decorate) calls to deploy.util.pps.path()
  to provide the search_paths attribute. To stop path objects from using the
  default search_paths, call the unwrap_path() method. If multiple pps
  handlers (i.e. CacheHandler and SearchPathsHandler) are being used, they must
  be unwrapped in the reverse order that they were wrapped to achieve the
  desired result.
  """
  def __init__(self, search_paths={}):
    self.search_paths = search_paths

    self.wrap_path()

  def wrap_path(self):
    "wrap deploy.util.pps.path function to set this instance's search_paths "
    "as the search_paths attribute for new path instances"
    setattr(deploy.util.pps, 'path', 
            self.path_wrapper(getattr(deploy.util.pps, 'path')))

  def unwrap_path(self):
    "restore original deploy.util.pps.path function"
    setattr(deploy.util.pps, 'path', _orig_path)

  def path_wrapper(self, fn):
    @wraps(fn)
    def wrapped(string, *args, **kwargs):
      if isinstance(string, deploy.util.pps.Path.BasePath):
        return string
      else:
        if 'search_paths' in kwargs:
          kwargs['search_paths'].update(self.search_paths)
        else:
          kwargs['search_paths'] = self.search_paths
        return fn(string, *args, **kwargs)
    return wrapped
