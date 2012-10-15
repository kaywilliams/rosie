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

from systemstudio.util.pps.UriTuple import urlunparse

from systemstudio.util.pps.Path import BasePath

from path_stat import RemotePath_Stat

from systemstudio.util.pps.Path import Path_IO     as RemotePath_IO
from systemstudio.util.pps.Path import Path_Printf as RemotePath_Printf
from systemstudio.util.pps.Path import Path_Walk   as RemotePath_Walk

class _RemotePath(BasePath):
  "String representation of HTTP file paths"
  # The following operations are redefinitions of those specified in
  # BasePath because of the protocol and realm portions of the URI.  In
  # most cases, they are simply the result of joining protocol, realm, and
  # the operation performed on path.

  # os functions
  def normcase(self):
    realm = self.hostname.lower()
    if self.username and self.password:
      realm = '%s:%s@%s' % (self.username, self.password, hostname)
    elif self.username:
      realm = '%s@%s' % (self.username, self.hostname)
    if self.port:
      realm = '%s:%s' % (realm, self.port)
    return self.__class__(urlunparse((self.protocol.lower(),
                                      realm,
                                      self.path or self._pypath.sep,
                                      self.params,
                                      self.query,
                                      self.fragment)))

class RemotePath(RemotePath_IO, RemotePath_Printf, RemotePath_Stat,
                 RemotePath_Walk, _RemotePath):
  pass
