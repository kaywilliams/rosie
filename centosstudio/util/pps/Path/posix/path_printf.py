#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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
import os

if os.name == 'posix':
  try:
    import grp
  except ImportError:
    grp = None
  try:
    import pwd
  except ImportError:
    pwd = None

from centosstudio.util.pps.Path.local import LocalPath_Printf

class PosixPath_Printf(LocalPath_Printf):
  """
  Additional formats:
   %g - group name, or id if group has no name
   %u - user name, or id if user has no name
  """
  def _printf_g(self):
    if os.name != 'posix':
      raise Exception("Cannot get '%%g' information for PosixPath on non-posix platform %s" % os.name)
    else:
      if not grp:
        raise NotImplementedError("'%g' format option not implemented on this platform")
      return grp.getgrgid(int(self._printf_G())).gr_name
  def _printf_u(self):
    if os.name != 'posix':
      raise Exception("Cannot get '%%u' information for PosixPath on non-posix platform %s" % os.name)
    else:
      if not pwd:
        raise NotImplementedError("'%f' format option not implemented on this platform")
      return pwd.getpwuid(int(self._printf_U())).pw_name
