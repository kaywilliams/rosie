#
# Copyright (c) 2012
# CentOS Solutions Foundation. All rights reserved.
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
from centosstudio.util.pps.Path.remote import RemotePath_Stat

from centosstudio.util.pps.PathStat.ftp import FtpPathStat

from error import error_transform

class FtpPath_Stat(RemotePath_Stat):

  def _mkstat(self, populate=False):
    stat = FtpPathStat(self)
    if populate: stat.stat()
    return stat

  # the following is defined for protection purposes
  _get_stat = RemotePath_Stat._get_stat

  _protect = ['_get_stat', '_mkstat']

for fn in FtpPath_Stat._protect:
  setattr(FtpPath_Stat, fn, error_transform(getattr(FtpPath_Stat, fn)))
