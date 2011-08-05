#
# Copyright (c) 2011
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

from openprovision.util.pps.util import urlunparse, _normpart

from openprovision.util.pps      import path as _path, register_scheme
from openprovision.util.pps.Path import BasePath

from path_io   import LocalPath_IO
from path_stat import LocalPath_Stat
from path_walk import LocalPath_Walk

from openprovision.util.pps.Path import Path_Printf as LocalPath_Printf

class _LocalPath(BasePath):
  "String representation of local file paths"
  def abspath(self):    return self.__class__(self._pypath.abspath(self))
  def normcase(self):   return self.__class__(self._pypath.normcase(self))
  def realpath(self):   return self.__class__(self._pypath.realpath(self))
  def expanduser(self): return self.__class__(self._pypath.expanduser(self))
  def expandvars(self): return self.__class__(self._pypath.expandvars(self))

  def expand(self):
    return self.expandvars().expanduser().normpath()

  def equivpath(self, other):
    try:
      return self.expand().abspath().realpath() == \
             _path(other).expand().abspath().realpath()
    except AttributeError:
      return False

  def relpath(self):
    return self.getcwd().relpathto(self)

  def relpathto(self, dst):
    start = self.abspath()
    end   = _path(dst)

    if hasattr(end, 'abspath'):
      end = end.abspath()
    else:
      assert end.isabs()

    return BasePath.relpathto(self, dst)

  def normpath(self):
    pt = self._urlparse()

    return self.__class__(
      urlunparse((pt.scheme != 'file' and pt.scheme or '',
                  pt.netloc != 'localhost' and pt.netloc or '',
                  self._pypath.normpath(pt.path),
                  _normpart(pt.params),
                  _normpart(pt.query),
                  _normpart(pt.fragment))))

  @classmethod
  def getcwd(cls):
    return cls(os.getcwd())

  def splitext(self):
    filename,ext = self._pypath.splitext(self)
    return self.__class__(filename), ext.__str__()

  def splitdrive(self):
    drive, rel = self._pypath.splitdrive(self)
    return drive, self.__class__(rel)

  ext   = property(lambda self: self.splitext()[1])
  drive = property(lambda self: self.splitdrive()[0])

  def touri(self):
    if not self.isabs():
      # convert relative paths to absolute before computing
      return BasePath.touri(self.abspath())
    else:
      return BasePath.touri(self)


class LocalPath(LocalPath_IO, LocalPath_Printf, LocalPath_Stat,
                LocalPath_Walk, _LocalPath):
  pass


def path(string):
  return PLATFORM_MAP[os.name](string)

from openprovision.util.pps.Path.nt    import NTPath
from openprovision.util.pps.Path.posix import PosixPath

PLATFORM_MAP = {
  'nt': NTPath,
  'posix': PosixPath
}

register_scheme('file', path)
register_scheme(None,   path)
