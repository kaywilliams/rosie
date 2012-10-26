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
import errno
import os

from repostudio.util.decorator import decorator

from repostudio.util.pps.Path.error import PathError

import sys
sys.path.insert(0, '/usr/share/rhn')
from up2date_client import up2dateErrors

@decorator
def error_transform(fn, *args, **kwargs):
  try:
    return fn(*args, **kwargs)
  except up2dateErrors.Error, e:
    raise transform(e, file=args[0])

def transform(e, file=None):
  """
  Transforms an up2dateError into a PathError
  """
  assert isinstance(e, up2dateErrors.Error)

  no = None

  if isinstance(e, up2dateErrors.PasswordError):
    no = errno.EACCES

  elif isinstance(e, up2dateErrors.CommunicationError):
    no = errno.ECOMM

  elif isinstance(e, up2dateErrors.FileNotFoundError):
    no = errno.ENOENT

  elif isinstance(e, up2dateErrors.DelayError):
    no = errno.ETIMEDOUT

  elif (isinstance(e, up2dateErrors.ValidationError) or
        isinstance(e, up2dateErrors.InvalidRegistrationNumberError) or
        isinstance(e, up2dateErrors.InvalidProductRegistrationError) or
        isinstance(e, up2dateErrors.OemInfoFileError) or 
        isinstance(e, up2dateErrors.NoBaseChannelError) or
        isinstance(e, up2dateErrors.SSLCertificateVerifyFailedError) or 
        isinstance(e, up2dateErrors.AuthenticationOrAccountCreationError) or
        isinstance(e, up2dateErrors.NoSystemIdError)
       ):
    no = errno.EINVAL

  elif (isinstance(e, up2dateErrors.NetworkError) or
        isinstance(e, up2dateErrors.InvalidRedirectionError)
       ):
    no = errno.ENETUNREACH

  return PathError(no, strerror=e.errmsg or os.strerror(no),
                       filename=file or e.filename,
                       exception=e)
