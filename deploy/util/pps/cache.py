#
# Copyright (c) 2015
# Deploy Foundation. All rights reserved.
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
cache.py - a handler for working with files in a cache. Includes a 
CopyCallback for caching files during copy operations.
"""

import hashlib
import time
import cPickle as pickle

from functools import wraps

import deploy.util

from deploy.util.progressbar   import ProgressBar

from deploy.util.sync.callback import SyncCallbackMetered

from deploy.util.pps import path as _orig_path

from deploy.util.pps.constants import *

DEFAULT_CACHE_DIR = '/tmp/.pps-cache'
DEFAULT_CACHE_SIZE = 500 * 1024**2 # 500 MB

MODE_COPY_ONLY  = 'copy-only'
MODE_COPY       = 'copy'
MODE_CACHE      = 'cache'


class CacheHandler(object):
  """
  A handler that provides information and utilities for storing, retrieving and
  managing quota for files in a cache. It is primarily intended for use with
  PPS, but can handle non-PPS activities as well, such as storing in-memory
  data to cached files using pickle (see the pkl_dump and pkl_load methods).
  
  Callers (such as PPS) can use the cache handler for determining where to
  store and retrieve cached files (cshfile), whether to force a new copies of
  files to be cached (force), and whether to retrieve files from the cache only
  (offline).

  CacheHandlers have the following variables:
   * cache_dir:          the directory into which to cache files
   * cache_max_size:     the maximum allowable size of the cache.  If the cache
                         gets above this size, files will be deleted, starting
                         with the least recently accessed file and continuing
                         until the self.cache_size < self.cache_max_size
   * cache_files:        dictionary of file => atime pairs
   * cache_size:         the current size of the cache
   * force:              if enabled, the handler deletes and recopies files to
                         the cache; this can be used, for example, to clear a
                         corrupted file
   * offline             if enabled, files will be accessed from the cache
                         only; if not in the cache, an error will be raised

  CacheHandler instances wrap (decorate) calls to deploy.util.pps.path(), i.e.
  to direct path objects to use the cache during copy, open and stat
  operations. To stop path objects from using the cache, call the unwrap_path()
  method.  If multiple pps handlers (i.e. CacheHandler and SearchPathsHandler)
  are being used, they must be unwrapped in the reverse order that they were
  wrapped to achieve the desired result.
  """
  def __init__(self, cache_dir=DEFAULT_CACHE_DIR,
                     cache_max_size=DEFAULT_CACHE_SIZE,
                     force=False,
                     offline=False):
    self.cache_dir = deploy.util.pps.path(cache_dir)
    self.cache_max_size = cache_max_size
    self.force = force
    self.offline=offline

    self.cache_dir.mkdirs()
    self.cache_files = {}
    for f in self.cache_dir.findpaths(type=TYPE_FILE):
      self.cache_files[f] = f.stat().st_atime

    self.cache_size = 0
    for f in self.cache_files:
      self.cache_size += f.stat().st_size

    self.wrap_path()

  def cshfile(self, file):
    return self.cache_dir / gen_hash(deploy.util.pps.path(file).normpath())

  def _touch(self, hash):
    "Touch a file in the cache list to update its atime"
    self.cache_files.setdefault(hash, time.time())

  def pkl_dump(self, data, key):
    """
    Dumps data to a file in the cache identified by 'key'. The key is an
    arbitrary string used in deriving the cached filename (via the cshfile
    method) As all cached files are stored in a single folder, callers must
    take care to provide a unique key.
    """
    with open(self.cshfile(key), 'wb') as fo:
      pickle.dump(data, fo)

  def pkl_load(self, key):
    """
    Loads and returns pickled data from a cached file. Returns None if the file
    does not exist.
    """
    fn = self.cshfile(key)
    if fn.exists():
      with open(self.cshfile(key), 'rb') as fo:
        return pickle.load(fo)
    else:
      return None

  def _enforce_quota(self, callback=None):
    """
    Enforce that self.cache_size must be less than self.cache_max_size
    by deleting files one at a time, based on their access time.  Older
    files are deleted first. Currently, no preference is given to files
    that are small or large, though a future improvement may also consider
    size in this metric.  This algorithm is somewhat vulnerable to other
    processes that may affect the access time; ideally, the cache handler
    itself would keep track of the access time separately from the OS's
    version.  This is relegated to a future improvement.
    """

    if self.cache_size > self.cache_max_size:
      sorted = [ (atime, f) for f, atime in self.cache_files.items() ]
      sorted.sort()
      # shrink the cache until we're below quota
      while self.cache_size > self.cache_max_size:
        _,cshfile = sorted.pop()
        fsize = cshfile.stat().st_size
        if hasattr(callback, '_cache_quota_rm'):
          callback._cache_quota_rm(cshfile, fsize, self.cache_size)
        cshfile.rm()
        self.cache_size -= fsize
        del self.cache_files[cshfile]

  def wrap_path(self):
    "wrap deploy.util.pps.path function to set this instance as the cache "
    "handler"
    setattr(deploy.util.pps, 'path', 
            self.path_wrapper(getattr(deploy.util.pps, 'path')))

  def unwrap_path(self):
    "restore original deploy.util.pps.path function"
    setattr(deploy.util.pps, 'path', _orig_path)

  def path_wrapper(self, fn):
    @wraps(fn)
    def wrapped(string, *args, **kwargs):
      if isinstance(string, deploy.util.pps.Path.BasePath):
        string.cache_handler=self
        return string
      else:
        kwargs['cache_handler'] = self
        return fn(string, *args, **kwargs)
    return wrapped

#------ CALLBACK ------#
class CachedCopyCallback(SyncCallbackMetered):
  """
  A callback for use with pps cached copy operations. Its primary feature is
  the consolidation of both operations into a single progress bar, as well
  as hiding the cached file's hash name (since it is ugly). Flexible to handle
  both cached and non-cached copies.
  """
  def __init__(self, verbose=False):
    SyncCallbackMetered.__init__(self, verbose=verbose,
      layout='%(title)-30.30s [%(bar)s] %(curvalue)5.5sB (%(time-elapsed)s)')

    self.mode = MODE_COPY_ONLY 

  def _start(self, size, text):
    self.filename = text
    self.bar = ProgressBar(self.layout, title=self.filename, size=size)
    self.bar.tags.get('curvalue').update(condense=True, ftype=str)
    self.bar.tags.get('maxvalue').update(condense=True, ftype=str)

    if not self.enabled: self.bar._fo = None

    self.bar.start()

  def _notify_cache(self):
    self.mode = MODE_CACHE

  def _notify_copy(self):
    self.mode = MODE_COPY

  def _cp_start(self, size, text, seek=0.0):
    if self.mode == MODE_COPY_ONLY:
      self.bar.tags.get('bar').update(unfilled=' ', filled='=')
    if self.mode == MODE_CACHE:
      self.bar.tags.get('bar').update(unfilled=' ', filled='-')
    elif self.mode == MODE_COPY:
      self.bar.tags.get('bar').update(unfilled='-', filled='=')

    self.bar.update(seek)

  def _cp_end(self, amount_read):
    # don't draw the bar; we're not finish()d yet
    pass

  def _end(self):
    self.bar.update(self.bar.status.size)
    self.bar.finish() # wait for bar to finish drawing
    del self.bar

  def _cache_quota_rm(self, file, file_size, cache_size):
    pass


# convenience functions
def gen_hash(text):
  return hashlib.md5(text).hexdigest()
