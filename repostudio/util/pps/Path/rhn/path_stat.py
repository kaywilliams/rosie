#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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
import time

from repostudio.util.pps         import path
from repostudio.util.pps.lib.rhn import validate_systemid

from repostudio.util.pps.Path.remote   import RemotePath_Stat

from repostudio.util.pps.PathStat.http import HttpPathStat

from error import error_transform

# if system doesn't have up2date_client; raises ImportError which is excepted
import sys
sys.path.insert(0, '/usr/share/rhn')
from up2date_client import config as rhnconfig
from up2date_client import rhnserver
from up2date_client import up2dateAuth
from up2date_client import up2dateErrors 

# set up default config file
rhnconfig.cfg = rhnconfig.Config(None)
rhnconfig.cfg['logFile'] = '/dev/null' # stop logging

class RhnPath_Stat(RemotePath_Stat):
  rhn_req_headers = ['X-RHN-Server-Id',
                     'X-RHN-Auth-User-Id',
                     'X-RHN-Auth',
                     'X-RHN-Auth-Server-Time',
                     'X-RHN-Auth-Expire-Offset']

  def __init__(self, string):
    self._rhn_headers = {} # dict of X-RHN-* headers
    self._headers = [] # list of (name,value) tuple headers

  def _get_systemid(self):
    if not systemids.has_key(self.channel):
      systemids[self.channel] = path('/etc/sysconfig/rhn/systemid')
    return systemids[self.channel]

  def _set_systemid(self, sysid):
    systemids[self.channel] = sysid

  systemid = property(_get_systemid, _set_systemid)

  def _login(self):
    global sessions
    if not self._rhn_headers:
      if ( # we don't have a session key
           ( not sessions.has_key(self.channel) )
           or
            # we have a session key but it timed out
           ( ( float(sessions[self.channel]['X-RHN-Auth-Server-Time']) +
               float(sessions[self.channel]['X-RHN-Auth-Expire-Offset'])
               < time.time() ) ) ):
        s = rhnserver.RhnServer()
        validate_systemid(self.systemid) # make sure systemid is ok first
        sessions[self.channel] = s.up2date.login(self.systemid.read_text())
      self._rhn_headers = sessions[self.channel]
      self._headers.extend([ (k,v) for k,v in self._rhn_headers.items() ])
    return self._rhn_headers

  def _mkstat(self, populate=False):
    # convert self to the 'real' path and return that stat
    return self.touri()._mkstat(populate=populate)

  _protect = ['_login', '_mkstat']

for fn in RhnPath_Stat._protect:
  setattr(RhnPath_Stat, fn, error_transform(getattr(RhnPath_Stat, fn)))

# cache of sessions, keyed by channel
sessions = {}
# cache of systemids, again by channel
systemids = {}
