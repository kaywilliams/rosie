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

import copy

from systembuilder.util.pps.Path.remote import RemotePath_IO

from systembuilder.util.pps.lib.http      import HttpFileObject
from systembuilder.util.pps.PathStat.http import HttpPathStat

from error import error_transform

class HttpPath_IO(RemotePath_IO):
  def __init__(self, path):
    # args to pass to open() and related calls; see lib/http.py for values
    self._foargs = {}
    # list of (key, value) header tuples
    self._headers = []

  # POST operations are not yet implemented, so most of these I/O functions
  # do not work

  # file metadata modification functions
  def utime(self, times):    raise HttpPostError
  def chmod(self, mode):     raise HttpPostError
  def chown(self, uid, gid): raise HttpPostError

  # file/directory creation/modification
  def rename(self, new): raise HttpPostError
  def mkdir(self, mode=0777): raise HttpPostError
  def rmdir(self):  raise HttpPostError
  def mknod(self):  raise HttpPostError
  def touch(self):  raise HttpPostError
  def remove(self): raise HttpPostError
  def unlink(self): raise HttpPostError

  def link(self, new):    raise HttpPostError
  def symlink(self, new): raise HttpPostError
  def readlink(self): return self.__class__(self)

  def open(self, mode='r', seek=None, **kwargs):
    if mode.startswith('r'):
      foargs = copy.copy(self._foargs)
      foargs.update(kwargs)
      fo = HttpFileObject(self, range=(seek, None), headers=self._headers,
                          **foargs)
      # cache stat results, since we're opening the url anyway
      stat = HttpPathStat(self)
      stat.stat(fo=fo)
      self._set_stat(stat)
      return fo
    else:
      raise HttpPostError

  _protect = ['utime', 'chmod', 'chown', 'rename', 'mkdir', 'rmdir', 'mknod',
              'touch', 'remove', 'unlink', 'link', 'symlink', 'readlink',
              'open']


for fn in HttpPath_IO._protect:
  setattr(HttpPath_IO, fn, error_transform(getattr(HttpPath_IO, fn)))


class HttpPostError(NotImplementedError):
  def __str__(self): return 'HTTP POST operations not yet implemented'
