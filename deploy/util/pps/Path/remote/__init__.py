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

import deploy.util

from deploy.util.pps.UriTuple import urlunparse

from deploy.util.pps.Path.cached import _CachedPath as CachedPath
from deploy.util.pps.Path.cached.path_io import CachedPath_IO as RemotePath_IO
from deploy.util.pps.Path.cached.path_stat import CachedPath_Stat as RemotePath_Stat

from deploy.util.pps.Path import Path_Printf as RemotePath_Printf
from deploy.util.pps.Path import Path_Walk   as RemotePath_Walk

class _RemotePath(CachedPath):
  """
  String representation of remote file paths.
  """
  def __new__(cls, value, **kwargs):
    return CachedPath.__new__(cls, value)

  # The following operations are redefinitions of those specified in
  # BasePath because of the protocol and realm portions of the URI.  In
  # most cases, they are simply the result of joining protocol, realm, and
  # the operation performed on path.

  # os functions
  def abspath(self): return self
  def expand(self):  return self

  def normcase(self):
    realm = self.hostname.lower()
    if self.username and self.password:
      realm = '%s:%s@%s' % (self.username, self.password, hostname)
    elif self.username:
      realm = '%s@%s' % (self.username, self.hostname)
    if self.port:
      realm = '%s:%s' % (realm, self.port)
    return self._new(urlunparse((self.protocol.lower(),
                                      realm,
                                      self.path or self._pypath.sep,
                                      self.params,
                                      self.query,
                                      self.fragment)))

  def _new(self, string):
    return deploy.util.pps.path(string)


class RemotePath(RemotePath_IO, RemotePath_Printf, RemotePath_Stat,
                 RemotePath_Walk, _RemotePath):
  pass
