#
# Copyright (c) 2012
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

from deploy.util.pps.PathSet   import PathSet

from deploy.util.pps.Path.error import PathError

from deploy.util.pps.Path.remote  import RemotePath_Walk

class FtpPath_Walk(RemotePath_Walk):

  def listdir(self):
    fo = self.open()

    try:
      if not self.isdir(): raise PathError(20, self)
      return PathSet([ self/f for f in fo.ftp.ftp.nlst() ])
    finally:
      fo.close()
