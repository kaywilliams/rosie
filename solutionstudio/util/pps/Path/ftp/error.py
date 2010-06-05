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
import errno
import os

from solutionstudio.util.decorator import decorator

from solutionstudio.util.pps.Path.error import PathError
from solutionstudio.util.pps.lib.ftp    import FtpFileObjectError

@decorator
def error_transform(fn, *args, **kwargs):
  try:
    return fn(*args, **kwargs)
  except FtpFileObjectError, e:
    raise transform(e, file=args[0])

def transform(e, file=None):
  """
  Transforms a FtpFileObjectError into a PathError

  This is still in a very rough stage, as I personally haven't experienced
  a number of urlgrabber errors.  Furthermore, some of the error mappings
  don't totally line up.
  """
  assert isinstance(e, FtpFileObjectError)

  no   = None
  msg  = None

  if e.errno == 1:    # malformed url
    no = errno.ENOENT
  elif e.errno == 4:
    no = errno.ECONNREFUSED
    msg = e.strerror
  elif e.errno == 5:  # timeout
    no  = errno.ETIME
    msg = e.strerror
  elif e.errno == 9 or e.errno == 12:
    no  = errno.EIO
    msg = e.strerror
  elif e.errno == 14: # HTTPError
    if e.code == 400 or e.code == 404:
      no = errno.ENOENT
    elif e.code == 401 or e.code == 403:
      no = errno.EACCES
    elif e.code == 416:
      no  = errno.EIO
      msg = e.strerror
    elif e.code in [500, 501, 502, 503, 504, 505]:
      no  = errno.ECONNABORTED
      msg = e.strerror
    file = e.exception.geturl()
  else:
    print "DEBUG: FtpFileObjectError.errno = %d" % e.errno
    print e
    print file
    raise e #!

  return PathError(no, strerror=msg or os.strerror(no),
                       filename=file or e.filename,
                       exception=e)
