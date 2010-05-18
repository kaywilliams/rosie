#
# Copyright (c) 2010
# Solution Studio Foundation. All rights reserved.
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

def raw_throttle(throttle=None, bandwidth=None):
  """
  Returns a float representing the bandwidth at which to throttle downloads.
  It is controlled by two numbers, bandwidth and throttle, above.  Bandwidth
  represents the max bandwidth of your connection (or the max you want to
  allot).  Throttle is a number; if it is an int, it is the byte/sec throttle
  limit to use; if it is a float, it is multiplied by the bandwidth to get
  the throttle limit, again in bytes/second.  If this function returns 0 or
  0.0, throttling is disabled.
  """
  # 0 or None for no throttling
  # integer for an absolute value in B/s
  # float for a multiplier on bandwidth
  if throttle  is None: throttle  = globals()['throttle']
  if bandwidth is None: bandwidth = globals()['bandwidth']
  if not throttle or throttle <= 0:
    return 0
  elif type(throttle) == type(0):
    return float(throttle)
  else: # throttle is a float
    return bandwidth * throttle

# the CACHE variable has the following structure:
# CACHE = { <path> : { <methodname> : meth(<path>, *args, **kwargs),
#                      <methodname> : meth(<path>, *args, **kwargs), } }
# That is, it is a cache of paths with the results of certain methods
# calls being stored.  Note that the args and kwargs are _not_ stored
# with the methodname; thus, it is recommended that you do not cache
# methods that accept arguments, for subsequent calls will ignore differing
# argument values, if present.
CACHE = {}

from solutionstudio.util.decorator import decorator

def cached(name=None, set=False, globally=False):
  """ 
  Function to return a decorator that caches results of function/method calls.

   name     : caching uses the function or method name as the key in the
              default case.  Override this behavior by providing a string
              to the 'name' argument.
   set      : this function or method, instead of getting the value from the
              cache, will set its value to whatever is returned
   globally : by default, caching is done at the path level - that is, the
              result is saved to PathObject.__cache_<name>.  In some cases, it
              is desirable to save a result globally so that any equivalent
              path can utilize the cache.  Set this argument to True in order
              to store a result in the global cache instead of the local cache
              (be mindful of the size of this global cache; it will persist
              throughout the python session).

  Cache methods can be strung together; for example:

    @cache()
    @cache(globally=True)
    def fn(...): ...

  The order that the caches are checked is the same as the order of the
  decorators; that is, in the above case, the local cache is checked before
  the global cache.
  """
  if globally:
    @decorator
    def new(meth, self, *args, **kwargs):
      # store a string, not the Path object itself
      key1 = str(self); key2 = name or meth.__name__
      if set or not CACHE.has_key(key1) or not CACHE[key1].has_key(key2):
        CACHE.setdefault(key1, {}).setdefault(key2, meth(self, *args, **kwargs))
      return CACHE[key1][key2]
  else:
    @decorator
    def new(meth, self, *args, **kwargs):
      key = '__cache_%s' % (name or meth.__name__)
      if set or not hasattr(self, key):
        setattr(self, key, meth(self, *args, **kwargs))
      return getattr(self, key)

  return new
