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

from systembuilder.util.pps          import register_scheme
from systembuilder.util.pps.lib.http import auth_handler

from path_io   import HttpPath_IO
from path_stat import HttpPath_Stat
from path_walk import HttpPath_Walk

from systembuilder.util.pps.Path.remote import _RemotePath as RemotePath
from systembuilder.util.pps.Path.remote import RemotePath_Printf as HttpPath_Printf

class HttpPath(HttpPath_IO, HttpPath_Printf, HttpPath_Stat,
               HttpPath_Walk, RemotePath):
  "String representation of HTTP file paths"
  pass

class HttpsPath(HttpPath):
  "String representation of HTTPS file paths"

  def set_auth(self, username, password):
    "Provides the default grabber object with a username, password pair to use"
    "when accessing this path"
    ##self.username, self.password = username, password #!
    auth_handler.add_password(None, self.realm, username, password)

def path(string, cls=HttpPath, stat=None):
  p = cls(string)
  if stat: p._set_stat(stat)
  return p

register_scheme('http',  path, None, {'cls': HttpPath})
register_scheme('https', path, None, {'cls': HttpsPath})
