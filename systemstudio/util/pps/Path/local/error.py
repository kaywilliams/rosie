#
# Copyright (c) 2012
# System Studio Project. All rights reserved.
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
from systemstudio.util.decorator import decorator

from systemstudio.util.pps.Path.error import PathError

@decorator
def error_transform(fn, *args, **kwargs):
  try:
    return fn(*args, **kwargs)
  except (OSError, IOError), e:
    raise transform(e)

def transform(e):
  assert isinstance(e, OSError) or isinstance(e, IOError)
  return PathError(e.errno, filename=e.filename, strerror=e.strerror,
                            exception=e)
