#
# Copyright (c) 2007, 2008
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
from os import strerror as os_strerror

class PathError(Exception):
  """
  Class of errors raised by Path objects.  Uses error codes as defined in the
  errno module.

  Path modules are responsible for converting any errors they raise into an
  equivalent PathError.  See error.py in either the file or http module for
  an example of how to do this.
  """
  def __init__(self, errno, filename=None, strerror=None, exception=None):
    errno = int(errno)
    self.args = [errno, strerror, filename]
    self.errno = errno
    self.filename = filename
    self.strerror = strerror or os_strerror(errno)
    self.exception = exception

  def __str__(self):
    if self.filename:
      return '[Errno %d]: %s: %s' % (self.errno, self.filename, self.strerror)
    else:
      return '[Errno %d]: %s' % (self.errno, self.strerror)
