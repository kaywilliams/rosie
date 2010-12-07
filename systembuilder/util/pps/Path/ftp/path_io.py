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
from solutionstudio.util.pps.Path.remote import RemotePath_IO

from solutionstudio.util.pps.lib.ftp import FtpFileObject

from solutionstudio.util.pps.PathStat.ftp import FtpPathStat

from error import error_transform

class FtpPath_IO(RemotePath_IO):

  def open(self, mode='r', seek=None):
    if mode.startswith('r'):
      fo = FtpFileObject(self, range=seek)
      # cache stat results, since we're opening the url anyway
      stat = FtpPathStat(self)
      stat.stat(fo=fo)
      self._set_stat(stat)
      return fo
    else:
      raise FtpPostError

  _protect = ['utime', 'chmod', 'chown', 'rename', 'mkdir', 'rmdir', 'mknod',
              'touch', 'remove', 'unlink', 'link', 'symlink', 'readlink',
              'open']


for fn in FtpPath_IO._protect:
  setattr(FtpPath_IO, fn, error_transform(getattr(FtpPath_IO, fn)))
