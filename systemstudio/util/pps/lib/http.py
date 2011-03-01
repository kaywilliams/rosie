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
# a lot of this code is shamelessly ripped from urlgrabber, though most of it
# has been stripped down to a more basic form

import copy
import socket
import string
import time
import urllib2
import urlparse

from httplib import HTTPException

from __init__ import raw_throttle

try:
  from urlgrabber.keepalive import HTTPHandler, HTTPSHandler
except ImportError, msg:
  keepalive_handlers = ()
else:
  keepalive_handlers = (HTTPHandler(), HTTPSHandler())

try:
  # add in range support conditionally too
  from urlgrabber.byterange import (HTTPRangeHandler, HTTPSRangeHandler,
                                    range_tuple_normalize, range_tuple_to_header,
                                    RangeError)
except ImportError, msg:
  range_handlers = ()
  RangeError = None
else:
  range_handlers = (HTTPRangeHandler(), HTTPSRangeHandler())

# global settings for pps
httpfo_params = dict(
  retries     = 5,
  timeout     = 15.0,
  keepalive   = True,
  close_connection = False,
  retry_codes = [-1,4,5,7,12],
  bandwidth   = 0, # connection bandwith in B/s; 0 for unlimited
  throttle    = 0,  # how to throttle
)


# authentication handler used by openers, below
# if necessary, add passwords to this auth handler for opening https locations
auth_handler = urllib2.HTTPBasicAuthHandler(
                 urllib2.HTTPPasswordMgrWithDefaultRealm()
               )


class HttpSyncRedirectHandler(urllib2.HTTPRedirectHandler):
  """Redirect handler class that determines if a url indicates a directory
  (by comparing the request url to the redirect url; if they are the same
  other than a trailing '/' on the redirect url, then the location is a
  directory; otherwise it is a file)."""
  def http_error_301(self, req, fp, code, msg, headers):
    result = urllib2.HTTPRedirectHandler.http_error_301(
      self, req, fp, code, msg, headers)

    if 'location' in headers:
      newurl = headers.getheaders('location')[0]
    elif 'uri' in headers:
      newurl = headers.getheaders('uri')[0]
    else:
      newurl = ''

    if newurl.rstrip('/') == req.get_full_url():
      result.isdir = True
    else:
      result.isdir = False

    return result

  http_error_302 = http_error_301


class HttpFileObject:
  def __init__(self, url, opener=None, range=None, headers=None, **kwargs):
    self.url,_ = _urlparse(url)

    foargs = copy.copy(httpfo_params)
    foargs.update(kwargs)

    self.retries     = foargs['retries']
    self.timeout     = foargs['timeout']
    self.keepalive   = foargs['keepalive']
    self.close_connection = foargs['close_connection']
    self.retry_codes = foargs['retry_codes']
    self.bandwidth   = foargs['bandwidth']
    self.throttle    = foargs['throttle']

    self.http_headers = headers or []

    self.fo = None
    self._pos = None
    self._rbuf = ''
    self._rbufsize = 1024*8
    self._ttime = time.time()
    self._tsize = 0
    self._opener = opener
    self._range = range_tuple_normalize(range)

    self._retry(self._do_open)

  def __getattr__(self, name):
    """'Pretend' we're a flo by looking up attributes on our file object if
    we don't define them ourselves"""
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
      try: self.fo.close_connection()
      except: pass

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
      except HttpFileObjectError, e:
        retrycode = e.errno

        if self.retries is None or tries >= self.retries: raise # break 2b
        if e.errno not in self.retry_codes: raise               # break 2c
      # break 2a (unexcepted error)

  def _get_opener(self):
    "Build a urllib2 OpenerDirector based on request options."
    if self._opener is None:
      handlers = []

      if keepalive_handlers and self.keepalive:
         handlers.extend(keepalive_handlers)
      if range_handlers and self._range:
         handlers.extend(range_handlers)

      handlers.append(HttpSyncRedirectHandler())
      handlers.append(auth_handler)
      self._opener = urllib2.build_opener(*handlers)
    return self._opener

  def _do_open(self, seek=None):
    """Open a file object and header object for the remote location this
    object represents"""
    opener = self._get_opener()

    req = urllib2.Request(self.url.__str__()) # build request object
    self._build_range(req, seek) # take care of byterange stuff
    for k,v in self.http_headers:
      req.add_header(k,v)

    (self.fo, self.hdr) = self._make_request(req, opener)

  def _build_range(self, req, seek=None):
    "add a Range header to the request, if necessary"
    if seek and range_handlers:
      req.add_header('Range', range_tuple_to_header((seek,)))
      self._pos = seek
      return

    if self._range:
      if not range_handlers:
        raise HttpFileObjectError(10, 'Byte range requested but range support unavailable')
      req.add_header('Range', range_tuple_to_header(self._range))
      self._pos = self._range[0]
    else:
      self._pos = 0

  def _make_request(self, req, opener):
    "Make the remote request and open a socket"
    try:
      if self.timeout:
        old_to = socket.getdefaulttimeout()
        socket.setdefaulttimeout(self.timeout)
        try:
          fo = opener.open(req)
        finally:
          socket.setdefaulttimeout(old_to)
      else:
        fo = opener.open(req)
      hdr = fo.info()
    except ValueError, e:
      raise HttpFileObjectError(1, 'Bad URL: %s' % e)
    except RangeError, e:
      raise HttpFileObjectError(9, str(e))
    except urllib2.HTTPError, e:
      new_e = HttpFileObjectError(14, str(e), req.get_full_url())
      new_e.code = e.code
      new_e.exception = e
      raise new_e
    except IOError, e:
      if hasattr(e, 'reason') and isinstance(e.reason, socket.timeout):
        raise HttpFileObjectError(12, 'Timeout: %s' % e)
      else:
        raise HttpFileObjectError(4, 'IOError: %s' % e)
    except OSError, e:
      raise HttpFileObjectError(5, 'OSError: %s' % e)
    except HTTPException, e:
      raise HttpFileObjectError(7, 'HTTP Exception (%s): %s' % \
                         (e.__class__.__name__, e))
    else:
      return (fo, hdr)

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
        raise HttpFileObjectError(12, 'Timeout: %s' % e)
      except socket.error, e:
        raise HttpFileObjectError(4, 'Socket Error: %s' % e)
      except IOError, e:
        raise HttpFileObjectError(4, 'IOError: %s' % e)
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
      except HttpFileObjectError, e:
        if e.errno == 12: # timeout
          self.close()
          self._do_open(self._pos or 0)
        raise
    finally:
      socket.setdefaulttimeout(old_to)


class HttpFileObjectError(IOError):
  """
  HttpFileObjectError error codes:
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


def _urlparse(url):
  "add the user/password pair from the url to auth_handler, if present"
  parts = urlparse.urlparse(str(url)) # stop the crazy Path proliferation!
  (scheme, host, path, parm, query, frag) = parts

  if '@' in host and auth_handler:
    try:
      user_pass, host = host.split('@', 1)
      if ':' in user_pass:
        user, password = user_pass.split(':', 1)
    except ValueError:
      raise HttpFileObjectError(1, 'Bad URL: %s' % url)

    auth_handler.add_password(None, host, user, password)

  # remove the username, password stuff from the url
  url = urlparse.urlunparse((scheme, host, path, parm, query, frag))
  return url, parts
