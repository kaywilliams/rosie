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
from repostudio.util.pps import register_scheme

from path_io     import FtpPath_IO
from path_stat   import FtpPath_Stat
from path_walk   import FtpPath_Walk

from repostudio.util.pps.Path.remote import _RemotePath as RemotePath
from repostudio.util.pps.Path.remote import RemotePath_Printf as FtpPath_Printf

class FtpPath(FtpPath_IO, FtpPath_Printf, FtpPath_Stat,
              FtpPath_Walk, RemotePath):
  "String representation of FTP file paths"
  pass

def path(string):
  return FtpPath(string)

register_scheme('ftp', path)
