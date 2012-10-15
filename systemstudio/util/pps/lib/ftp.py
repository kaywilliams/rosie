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

from urllib import ftpwrapper

import copy
import ftplib
import socket
import string
import time

from __init__ import raw_throttle

# global settings for pps
ftpfo_params = dict(
  retries = 5,
  timeout = 15.0,
  close_connection = False,
  retry_codes = [-1,4,5,7,12],
  bandwidth = 0,
  throttle = 0,
)


class FtpFileObject:
  def __init__(self, url, range=None, **kwargs):
    self.url = url
    self.range = range

    foargs = copy.copy(ftpfo_params)
    foargs.update(kwargs)

    self.retries     = foargs['retries']
    self.timeout     = foargs['timeout']
    self.close_connection = foargs['close_connection']
    self.retry_codes = foargs['retry_codes']
    self.bandwidth   = foargs['bandwidth']
    self.throttle    = foargs['throttle']

    self.ftp = ftpwrapper(self.url.username, self.url.password,
                          self.url.hostname, self.url.port,
                          self.url.path.dirname.splitpath())

    self.fo = None
    self._pos = None
    self._rbuf = ''
    self._rbufsize = 1024*8
    self._ttime = time.time()
    self._tsize = 0

    self._retry(self._do_open)

  def __getattr__(self, name):
    "'Pretend we're a flo by looking up attrs on self.fo"
    if hasattr(self.fo, name):
      return getattr(self.fo, name)
    raise AttributeError, name

  def read(self, amt=None):
    if amt and amt < 0: amt = None
    self._retry(self._retry_fill_buffer, amt)

    if amt is None:
      s, self._rbuf = self._rbuf, ''
    else:
      s, self._rbuf = self._rbuf[:amt], self._rbuf[amt:]
    return s

  def readline(self, limit=-1):
    i = string.find(self._rbuf, '\n')
    while i < 0 and not (0 < limit <= len(self._rbuf)):
      L = len(self._rbuf)
      self._retry(self._retry_fill_buffer, L + self._rbufsize)
      if not len(self._rbuf) > L: break
      i = string.find(self._rbuf, '\n', L)

    if i < 0: i = len(self._rbuf)
    else: i = i+1
    if 0 <= limit < len(self._rbuf): i = limit

    s, self._rbuf = self._rbuf[:i], self._rbuf[i:]
    return s

  def tell(self):
    return self._pos

  def close(self):
    self.fo.close()
    if self.close_connection:
      try: self.ftp.ftp.quit()
      except: pass

  def _do_open(self, seek=None):
    # doesn't currently handle seek #!
    self.fo,_ = self.ftp.retrfile(self.url.basename, 'I')
    self._pos = seek or 0

  def _retry(self, func, *args, **kwargs):
    """try func(*args, **kwargs) up to retries times, excepting certain
    errors, such as timeouts."""
    tries = 0
    while True:
      # there are only two ways out of this loop.  The second has
      # several "sub-ways"
      #  1) via the return in the "try" block
      #  2) by some exception being raised
      #     a) an excepton is raised that we don't "except"
      #     b) we're not retry-ing or have run out of retries
      #     c) the HttpFileObjectError code is not in retry_codes
      tries += 1
      exception = None
      retrycode = None
      try:
        return apply(func, args, kwargs) # break 1
      except FtpFileObjectError, e:
        retrycode = e.errno

        if retries is None or tries >= self.retries: raise # break 2b
        if e.errno not in self.retry_codes: raise          # break 2c
      # break 2a (unexcepted error)

  def _fill_buffer(self, amt=None):
    """fill the buffer to contain at least 'amt' bytes by reading
    from the underlying file object.  If amt is None, then it will
    read until it gets nothing more."""
    # the _rbuf test is only in this first 'if' for speed.  It's not
    # logically necessary
    if self._rbuf and amt is not None:
      L = len(self._rbuf)
      if amt > L:
        amt = amt - L
      else:
        return

    # if we've made it here, then we don't have enough in the buffer
    # and we need to read more.

    buf = [self._rbuf]
    bufsize = len(self._rbuf)
    while amt is None or amt:
      # first, delay if necessary for throttling reasons
      t = raw_throttle(self.throttle, self.bandwidth)
      if t:
        diff = self._tsize/t - (time.time() - self._ttime)
        if diff > 0: time.sleep(diff)
        self._ttime = time.time()

      # now read some data, up to self._rbufsize
      if amt is None: readamount = self._rbufsize
      else:           readamount = min(amt, self._rbufsize)

      try:
        new = self.fo.read(readamount)
      except socket.timeout, e:
        raise FtpFileObjectError(12, 'Timeout: %s' % e)
      except socket.error, e:
        raise FtpFileObjectError(4, 'Socket Error: %s' % e)
      except IOError, e:
        raise FtpFileObjectError(4, 'IOError: %s' % e)
      newsize = len(new)
      if not newsize: break # no more to read

      self._pos += newsize
      if amt: amt = amt - newsize
      buf.append(new)
      bufsize = bufsize + newsize
      self._tsize = newsize

    self._rbuf = string.join(buf, '')

  def _retry_fill_buffer(self, amt=None):
    old_to = socket.getdefaulttimeout()
    if self.timeout:
      socket.setdefaulttimeout(self.timeout)
    try:
      try:
        self._fill_buffer(amt)
      except FtpFileObjectError, e:
        if e.errno == 12: # timeout
          self.close()
          self._do_open(self._pos or 0)
        raise
    finally:
      socket.setdefaulttimeout(old_to)

class FtpFileObjectError(IOError):
  """
  FtpFileObjectError error codes:
    0  - everything looks good (you should never see this)
    1  - malformed url
    4  - IOError on fetch
    5  - OSError on fetch
    7  - HTTPException
    9  - Requested byte range not satisfiable.
    10 - Byte range requested, but range support unavailable
    12 - Socket timeout
    14 - HTTPError (includes .code and .exception attributes)

  Retry codes (< 0)
    -1 - retry the download, unknown reason
  """
  pass
