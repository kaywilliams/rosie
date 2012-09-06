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

import posixpath

from path_io     import PosixPath_IO
from path_printf import PosixPath_Printf

from repostudio.util.pps.Path.local import _LocalPath     as LocalPath
from repostudio.util.pps.Path.local import LocalPath_Stat as PosixPath_Stat
from repostudio.util.pps.Path.local import LocalPath_Walk as PosixPath_Walk

class PosixPath(PosixPath_IO, PosixPath_Printf, PosixPath_Stat,
                PosixPath_Walk, LocalPath):
  "String representation of local file paths"
  _pypath = posixpath
