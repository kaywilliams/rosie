#
# Copyright (c) 2010
# Solution Studio Foundation. All rights reserved.
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

import ntpath

from path_printf import NTPath_Printf

from solutionstudio.util.pps.util import urlunparse

from solutionstudio.util.pps.Path.local import _LocalPath     as LocalPath
from solutionstudio.util.pps.Path.local import LocalPath_IO   as NTPath_IO
from solutionstudio.util.pps.Path.local import LocalPath_Stat as NTPath_Stat
from solutionstudio.util.pps.Path.local import LocalPath_Walk as NTPath_Walk

class NTPath(NTPath_IO, NTPath_Printf, NTPath_Stat,
             NTPath_Walk, LocalPath):
  "String representation of local file paths on the nt platform"
  _pypath = ntpath

  def splitunc(self):
    unc, rest = self._pypath.splitunc(self)
    return unc, self.__class__(rest)

  uncshare = property(lambda self: self.splitunc()[0])

  def splitroot(self):
    # absolute paths
    # drive
    _path = self.__class__(self._urlparse().path)
    if _path.startswith(self._pypath.altsep): # uri syntax
      drive, path = _path.lstrip(self._pypath.altsep).splitdrive()
      sep = self._pypath.altsep
    else:
      drive, path = _path.splitdrive()
      sep = self._pypath.sep
    if drive:
      root = self.__class__(urlunparse((self.scheme,
                                        self.netloc,
                                        drive+sep,
                                        '','','')))
      return root, path.lstrip(self._pypath.sep+self._pypath.altsep)
    # unc share
    unc, path = self.splitunc()
    if unc:
      return (self.__class__(unc),
              path.lstrip(self._pypath.sep+self._pypath.altsep))

    # relative path
    return self.__class__(''), self.__class__(self._urlparse().path)
