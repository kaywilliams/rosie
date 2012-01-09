#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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
path - the main PPS path interface and modules

Path objects consist of a number of superclass Path modules which define
some subset of the entire interface and a single subclass that inherits
method definitions from them.  In most cases, there is little to no code
in the subclass module itself.

The Path interface defines a few methods completely; these 'algorithm
methods' will work perfectly for any Path type that completely and correctly
implements the methods they use.  'Operation methods', on the other hand,
are undefined, usually raising a NotImplementedError.  These methods must
be implemented in a subclass as they usually have protocol-specific
requirements on their output.

Path objects are a subclass of the str builtin.  The primary benefit of
this is that they can be used directly whenever a string is normally
required; for example, you can pass a Path object to a regular expression
processor and get back the expected result, or you can use any of str's
normal methods, such as upper(), split(), and the like.
"""

import errno
import os.path

from centosstudio.util.pps import path

from centosstudio.util.pps.lib import cached, CACHE

from centosstudio.util.pps.constants  import _base
from centosstudio.util.pps.PathTokens import PathTokens
from centosstudio.util.pps.Path.error import PathError
# imported at the end to avoid circular ref
#from centosstudio.util.pps.util       import urlparse, urlunparse, _normpart
#from centosstudio.util.pps.UriTuple   import UriTuple

from centosstudio.util.pps.Path.path_io     import Path_IO
from centosstudio.util.pps.Path.path_printf import Path_Printf
from centosstudio.util.pps.Path.path_stat   import Path_Stat
from centosstudio.util.pps.Path.path_walk   import Path_Walk

class BasePath(_base):
  """
  Common superclass for string representations of a path
  """
  _pypath = os.path

  def __str__(self):
    return _base.__str__(self)
  def __repr__(self):
    return '%s(%s)' % (self.__class__.__name__, _base.__repr__(self))

  def __div__(self, other):
    """
    This method allows paths to be joined by the / operator.  For example,
    path('/var/www/html') / 'hi' returns path('/var/www/html/hi')
    """
    if not other: return self.__class__(self)
    other = path(other)
    if other.isabs(): return other
    return self.__class__(self._pypath.join(self.__str__(), other.__str__()))
  __truediv__ = __div__ # works in either normal or 'true' division mode
  def __floordiv__(self, other):
    """
    Same as above, except all absolute paths are treated as relative paths.
    For example, path('/var') / '/www' returns path('/www'), while
    path('/var/') // '/www' returns path('/var/www')
    """
    if not other: return self.__class__(self)
    other = path(other)
    return self.__class__(self._pypath.join(self.__str__(), other.path.__str__()))
  def __rdiv__(self, other):
    """
    Allows paths to be joined onto strings; for example, 'a/b' /
    path('c/d') = path('a/b/c/d')
    """
    return self.__class__(other).__div__(self)
  __rtruediv__ = __rdiv__
  def __rfloordiv__(self, other):
    "Same as __rdiv__, except using the __floordiv__ operator ('//')"
    return self.__class__(other).__floordiv__(self)

  @property
  def dirname(self):
    """
    Returns the first part of the tuple returned by path.splitpath().
    This is accessible in path objects via the .dirname property.
    """
    return self.__class__(self.splitpath()[0] or self._pypath.curdir)
  @property
  def basename(self):
    """
    Returns the second part of the tuple returned by path.splitpath().
    This is accessible in path objects via the .basename property.
    """
    return self.__class__(self.splitpath()[1])

  def splitpath(self):
    """
    (dirname, basename) = path.split()

    Returns a tuple of dirname, basename for the given path object.  Unlike
    os.path.splitpath(), this method is insensitive to trailing slashes;
    that is,

      (path('/a/b'), path('c')) == path('/a/b/c').splitpath()
                                == path('/a/b/c/').splitpath()

    Additionally, calling .spitpath() on a path object at the root returns
    a tuple where both elements are a copy of the root; for example:

      (path('/'), path('/')) == path('/').splitpath()

    Invariant: dirname / basename == path.normpath()
    Invariant: dirname == basename for path.splitpath() when path
               consists of a single token, the root.
    """
    norm = self.normpath(); root = self.root
    if norm == root: return (root, root)
    dirname, basename = self._pypath.split(norm.__str__())
    return self.__class__(dirname), self.__class__(basename)

  @cached()
  def splitall(self):
    """
    PathTokens(path) = path.splitall()

    Allows easy iteration over each element in the path.  An element is
    defined as the portions of the path between path._pypath.sep ('/' in
    posix paths, r'\'; for ntpaths, and so on).

      # absolute paths
      [ path('/'), path('var'), path('www'), path('html') ] ==
        [ x for x in path('/var/www/html').splitall() ]

      # relative paths
      [ path('var'), path('www'), path('html') ] ==
        [ x for x in path('var/www/html').splitall() ]

    The split result is cached in path._splitcache so that multiple calls
    don't perform the same computation repeatedly.

    See the PathTokens class for more details on the available methods.
    """
    parts = []
    root, cur = self.splitroot()
    while cur and cur != self._pypath.curdir and cur != self._pypath.pardir:
      cur, basename = cur.splitpath()
      parts.append(basename)
    if root: parts.append(root)
    parts.reverse()
    return PathTokens(parts)

  def joinpath(self, *parts):
    """
    path('/var/www/html') = path('/var').joinpath('www', 'html')

    Analog to os.path.join(); joins each of the arguments given to the
    path object.  Joins are performed using the __div__ operator, meaning
    that absolute parts will overwrite previous path elements.

    Invariant: path.joinpaths(*parts) == for part in parts: path = path/part
    """
    p = self
    for part in parts:
      p = p / part
    return p

  @property
  def root(self):
    """
    Returns the first element of the tuple returned by path.splitroot().
    If this value is path('') (relative paths), returns None
    """
    return self.splitroot()[0] or None

  @property
  def path(self):
    """
    Returns the second element of the tuple returned by path.splitroot().
    Always returns a path object, even if it is empty.
    """
    return self.splitroot()[1]

  def splitroot(self):
    """
    (root, relpath) = path.splitroot()

    Splits a path into a root and relative path tuple.  The root of a path
    varies depending on the path type, but it is usually the entire path up
    until the first path separator.  relpath is always a relative path.

    If path is a relative path, then root will be path('').

    Invariant: root / relpath = path.normpath()
    """
    if self._urlparse().path.startswith(self._pypath.sep):
      root = self.__class__(urlunparse((self.scheme,
                                        self.netloc,
                                        self._pypath.sep,
                                        '', '', '')))
      path = self.__class__(self._urlparse().path.lstrip(self._pypath.sep))
      return root, path
    else:
      return self.__class__(''), self.__class__(self._urlparse().path)

  # path manipulation functions
  def normcase(self):
    """
    Performs normalization on the case of characters in the path.  The
    effect of this operation is highly dependent on the path type (some
    paths are case sensitive while others are not).
    """
    return self.__class__(self)
  def normpath(self):
    """
    Returns a normalized version of the path.  Like .normcase(), above,
    the effect of .normpath() is highly dependent on the path type.
    Most path types will do replacement of multiple path separators,
    resolution of curdirs and pardirs ('.' and '..' in posix), and ordering
    of arguments (like params and queries in http urls).

    Varies from the posix standard in that normalization of a directory
    path does not return path('somepath/.')
    """
    pt = self._urlparse()
    np = self._pypath.normpath(pt.path)
    np = np.replace('//', '/') # replace initial '//' if present
    if np == self._pypath.curdir: np = '' # don't include single curdir

    return self.__class__(
      urlunparse((pt.scheme,
                  pt.netloc,
                  np,
                  _normpart(pt.params),
                  _normpart(pt.query),
                  _normpart(pt.fragment))))

  def isabs(self):
    "Returns whether the path is an absolute path (path.root is not None)"
    return self.root and True or False

  def abspath(self):
    "Returns an absolute version of the path."
    if self.isabs():
      return self.__class__(self)
    else:
      raise PathError(errno.EINVAL, "Unable to determine absolute path for non-local file '%s'" % self)

  def relpath(self):
    "Returns a relative version of the path."
    return self.__class__(self)

  def relpathto(self, dst):
    """
    Returns a path object that represents one possible relative path from
    the path to dst.  If it is impossible to reach dst from the path using
    a relative path, then an absolute path to dst is returned (this can
    happen, for example, if the roots of the two paths differ).  If the
    path and dst are equivalent paths, returns path(self._pypath.curdir)
    ('.' in posix).
    """
    start = self
    end   = path(dst)

    if start.isabs():
      assert end.isabs()

    if start.root != end.root:
      return end

    if start.equivpath(end):
      return self.__class__(self._pypath.curdir)

    i = 0
    for s,e in zip(start.splitall(), end.splitall()):
      if s != e:
        break
      i += 1

    dirs = self.__class__(self._pypath.sep.join(
                          [self._pypath.pardir] * (len(start.splitall()) - i)))
    dirs = dirs / end.splitall()[i:]
    return dirs

  def relpathfrom(self, src):
    """
    Inverse of .relpathto()

    Invariant: path.relpathto(dst) == dst.relpathfrom(path)
    """
    return path(src).relpathto(self)

  def equivpath(self, other):
    """
    Returns True iff self and other are equivalent paths.  Like .normpath()
    and .normcase(), above, the behavior of this method is largely path-type
    dependant.
    """
    return self.normpath() == path(other).normpath()

  @cached()
  def _urlparse(self):
    return UriTuple(urlparse(self))

  @property
  def protocol(self): return self._urlparse().scheme or None
  scheme = protocol # alias for parity with uritup
  @property
  def realm(self):    return self._urlparse().netloc or None
  netloc = realm # aliaes for parity with uritup
  @property
  def params(self):   return self._urlparse().params or None
  @property
  def query(self):    return self._urlparse().query or None
  @property
  def fragment(self): return self._urlparse().fragment or None
  @property
  def username(self): return self._urlparse().username or None
  @property
  def password(self): return self._urlparse().password or None
  @property
  def hostname(self): return self._urlparse().hostname or None
  @property
  def port(self):     return self._urlparse().port or None

  def touri(self):
    """Return a URI representation of the path"""
    if self.isabs():
      return self.__class__(self._urlparse().geturi())
    else:
      raise ValueError("Cannot convert relative path '%s' to URI" % self)


  # str/unicode compat methods

  # The methods defined below are a compatability layer to ensure that paths
  # appear as strings (or unicode) whenever possible while maintaining their
  # unique methods.

  def __add__(self, other):
    return self.__class__(_base.__add__(self, other))
  def __getitem__(self, index):
    return self.__class__(_base.__getitem__(self, index))
  def __getslice__(self, low, high):
    return self.__class__(_base.__getslice__(self, low, high))
  def lower(self):
   return self.__class__(_base.lower(self))
  def lstrip(self, *args):
    return self.__class__(_base.lstrip(self, *args))
  def replace(self, *args):
    return self.__class__(_base.replace(self, *args))
  def rstrip(self, *args):
    return self.__class__(_base.rstrip(self, *args))
  def strip(self, *args):
   return self.__class__(_base.strip(self, *args))
  def swapcase(self):
   return self.__class__(_base.swapcase(self))
  def upper(self):
    return self.__class__(_base.upper(self))

  # caching methods
  def cache(self, key, value, globally=False):
    "Store an item in the cache for a cached method"
    if globally:
      CACHE.setdefault(self, {}).setdefault(key, value)
    else:
      setattr(self, '__cache_%s' % key, value)

  def uncache(self, key):
    "Delete an item in the method cache"
    try:
      del CACHE[self][key]
    except KeyError:
      pass
    try:
      delattr(self, '__cache_%s' % key)
    except AttributeError:
      pass

# imported last to avoid circular ref
from centosstudio.util.pps.UriTuple import UriTuple
from centosstudio.util.pps.util     import urlparse, urlunparse, _normpart
