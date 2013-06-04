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

from deploy.util.pps          import path as _path, register_scheme
from deploy.util.pps.lib.http import auth_handler
from deploy.util.pps.util     import urlunparse

from path_io   import RhnPath_IO
from path_stat import RhnPath_Stat

from deploy.util.pps.Path.http import HttpPath_Printf as RhnPath_Printf

from deploy.util.pps.Path.remote import _RemotePath     as RemotePath
from deploy.util.pps.Path.remote import RemotePath_Walk as RhnPath_Walk

class RhnPath(RhnPath_IO, RhnPath_Printf, RhnPath_Stat,
              RhnPath_Walk, RemotePath):
  "String representation of rhn file paths"

  default_realm = 'xmlrpc.rhn.redhat.com'
  rpc_prefix    = '/XMLRPC/GET-REQ'

  def __init__(self, string, **kwargs):
    RemotePath.__init__(self, string, **kwargs)
    RhnPath_Stat.__init__(self, string)

  @property
  def channel(self):
    if self.isabs():
      return self.splitall()[:2] # root plus first path item = channel
    else:
      raise ValueError("Cannot compute channel of relative RHN path")

  def touri(self):
    if self.scheme == 'rhns':
      scheme = 'https'
    else:
      scheme = 'http'

    uri = _path(urlunparse((scheme,
                            self.realm or self.default_realm,
                            self.rpc_prefix / self.path,
                            '', '', '')))

    # populate uri's headers automatically
    self._login()
    uri._headers = self._headers

    return uri


class RhnsPath(RhnPath):
  "String representation of rhns file paths"

  def __init__(self, string, **kwargs):
    RhnPath.__init__(self, string, **kwargs)


def path(string, cls=RhnPath, systemid=None, **kwargs):
  p = cls(string, **kwargs)
  if systemid:
    p._systemid = _path(systemid)
  return p

register_scheme('rhn',  path, None, {'cls': RhnPath})
register_scheme('rhns', path, None, {'cls': RhnsPath})
