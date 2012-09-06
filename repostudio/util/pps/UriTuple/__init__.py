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
"""
UriTuple - a subclass of tuple that contains interesting information about
various parts of a URI

Based on some functions/classes in urlparse
"""

from os.path import normpath

from repostudio.util.pps.util import urlparse, urlunparse

class UriTuple(tuple):
  """Tuple of the various pieces of a split URI.  Based on urlparse.BaseResult,
  which only exists in Python 2.5"""
  __slots__ = ()

  def geturl(self):
    return urlunparse(self)

  def geturi(self):
    "Like geturl except this returns a valid uri"
    return urlunparse((self.scheme and self.scheme or 'file',
                       self.netloc and self.netloc or 'localhost',
                       self.path.replace('\\', '/'), # fix up NT names
                       self.params,
                       self.query,
                       self.fragment))

  @property
  def scheme(self):   return self[0]
  @property
  def netloc(self):   return self[1]
  @property
  def path(self):     return self[2]
  @property
  def params(self):   return self[-3]
  @property
  def query(self):    return self[-2]
  @property
  def fragment(self): return self[-1]

  @property
  def username(self):
    netloc = self.netloc
    if '@' in netloc:
      userinfo = netloc.split('@', 1)[0]
      if ':' in userinfo:
        userinfo = userinfo.split(':', 1)[0]
      return userinfo
    return None

  @property
  def password(self):
    netloc = self.netloc
    if '@' in netloc:
      userinfo = netloc.split('@', 1)[0]
      if ':' in userinfo:
        return userinfo.split(':', 1)[1]
    return None

  @property
  def hostname(self):
    netloc = self.netloc
    if '@' in netloc:
      netloc = netloc.split('@', 1)[1]
    if ':' in netloc:
      netloc = netloc.split(':', 1)[0]
    return netloc.lower() or None

  @property
  def port(self):
    netloc = self.netloc
    if '@' in netloc:
      netloc = netloc.split('@', 1)[1]
    if ':' in netloc:
      port = netloc.split(':', 1)[1]
      return int(port, 10)
    return None
