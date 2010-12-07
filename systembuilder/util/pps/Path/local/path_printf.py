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
import os

if os.name == 'nt':
  try:
    import win32security
  except ImportError:
    win32security = None
elif os.name == 'posix':
  try:
    import grp
  except ImportError:
    grp = None
  try:
    import pwd
  except ImportError:
    pwd = None

from solutionstudio.util.pps.path import path_printf

PROTECT = []

class FilePath_Printf(path_printf.Path_Printf):
  """
  Additional formats:
   %g - group name, or id if group has no name
   %u - user name, or id if user has no name
  """
  def _printf_g(self):
    if os.name == 'nt':
      raise Exception("'%g' format option can't be used on the 'nt' platform")
    else:
      if not grp:
        raise NotImplementedError("'%g' format option not implemented on this platform")
      return grp.getgrgid(int(self._printf_G())).gr_name
  def _printf_u(self):
    if os.name == 'nt':
      if not win32security:
        raise Exception("'%g' format option requires win32all to be installed")
      desc = win32security.GetFileSecurity(self.normpath(), win32security.OWNER_SECURITY_INFORMATION)
      sid = desc.getSecurityDescriptorOwner()
      account, domain, _ = win32security.LookupAccountSid(None, sid)
      return domain + u'\\' + account
    else:
      if not pwd:
        raise NotImplementedError("'%f' format option not implemented on this platform")
      return pwd.getpwuid(int(self._printf_U())).pw_name
