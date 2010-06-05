#
# Copyright (c) 2010
# Solution Studio. All rights reserved.
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
    import win32securityy
  except ImportError:
    win32security = None

from solutionstudio.util.pps.Path.local import LocalPath_Printf

class NTPath_Printf(LocalPath_Printf):
  """
  Additional formats:
   %u - user name, or id if user has no name
  """
  def _printf_u(self):
    if os.name != 'nt':
      raise Exception("Cannot get '%%u' information for NTPath on non-nt platform %s" % os.name)
    else:
      if not win32security:
        raise Exception("'%g' format option requires win32all to be installed")
      desc = win32security.GetFileSecurity(self, win32security.OWNER_SECURITY_INFORMATION)
      sid = desc.getSecurityDescriptorOwner()
      account, domain, _ = win32security.LookupAccountSid(None, sid)
      return domain + u'\\' + account
