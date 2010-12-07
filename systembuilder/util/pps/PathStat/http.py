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
"http.py - implementation of PathStat for http locations"

import calendar
import rfc822
import stat
import time

from solutionstudio.util.pps.lib.http import HttpFileObject

from __init__ import PathStat

class HttpPathStat(PathStat):
  """
  HttpPathStat fully implements the PathStat interface.  However, some of
  the fields present in a normal PathStat result are meaningless or
  impossible to determine on http locations.  These include st_ctime,
  st_dev, st_gid, st_ino, st_nlink, and st_uid; they are represented by -1
  in the resulting tuple.
  """
  def stat(self, fo=None):
    """
    HttpPathStat's stat() call allows passing a file object in the fo
    argument, which can be an open file-like object on the file located at
    HttpPathStat.uri. This allows a slight bit of optimization by
    minimizing HTTP requests made on the server.  If fo is None,
    HttpPathStat creates its own connection.
    """
    if not fo:
      stat_fo = HttpFileObject(self.uri, headers=self.uri._headers)
    else:
      stat_fo = fo

    self._hdr = stat_fo.hdr

    if self.uri.endswith('/') or (hasattr(stat_fo, 'isdir') and stat_fo.isdir):
      mode = stat.S_IFDIR
    else:
      mode = stat.S_IFREG

    # if we weren't passed a file object, close the one we created
    if not fo: stat_fo.close()

    # set atime
    atime = int(time.time())

    # set mtime
    if self._hdr.has_key('last-modified'):
      mtime = int(calendar.timegm(
                   rfc822.parsedate_tz(self._hdr.getheader('last-modified'))
                 ))
    else:
      mtime = -1

    # set size
    if self._hdr.has_key('content-length'):
      if not mode & stat.S_IFDIR:
        size = int(self._hdr.getheader('content-length'))
      else:
        size = 0 # set size to zero on directories; best approximation we can make
    else:
      size = -1

    self._stat = list((mode, -1, -1, -1, -1, -1, size, atime, mtime, -1))
