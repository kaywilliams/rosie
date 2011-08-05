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
"""
cache.py - a CopyHandler and SyncCallback for caching files as they are synched
to improve performance on subsequent sync() calls
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '0.8.1'
__date__    = 'August 22nd, 2007'

import hashlib
import time

from systemstudio.util.progressbar import ProgressBar

from systemstudio.util.sync.__init__ import CopyHandler, SyncOperation, mirror_updatefn
from systemstudio.util.sync.callback import SyncCallbackMetered

from systemstudio.util.pps import path

from systemstudio.util.pps.constants import *

DEFAULT_CACHE_DIR = '/tmp/.sync-cache'
DEFAULT_CACHE_SIZE = 500 * 1024**2 # 500 MB

MODE_COPY  = 'copy'
MODE_CACHE = 'cache'

#------ COPY HANDLER ------#
class CachedSyncHandler(CopyHandler):
  """
  A handler that performs file caching during the sync process.  Subsequent
  calls to sync() with this handler will copy files directly from the cache,
  unless the file in the source has changed.  This can dramatically increase
  speeds for normally slow sync operations, such as those over a non-local
  network.

  CachedSyncHandlers have the following variables:
   * cache_dir:          the directory into which to cache files
   * cache_max_size:     the maximum allowable size of the cache.  If the cache
                         gets above this size, files will be deleted, starting
                         with the least recently accessed file and continuing
                         until the self.cache_size < self.cache_max_size
   * cache_files:        dictionary of file => atime pairs
   * cache_size:         the current size of the cache
   * cache_copy_handler: the CopyHandler object used to perform copying from the
                         cache to the destination.  Defaults to the CopyHandler
                         defined in __init__
   * cache_updatefn:     the updatefn to use for handling updates in the cache
   * force:              if enabled, the handler deletes and recopies files to
                         the cache; this can be used, for example, to clear a
                         corrupted file
  """
  def __init__(self, cache_dir=DEFAULT_CACHE_DIR, cache_max_size=DEFAULT_CACHE_SIZE,
                     cache_copy_handler=None, force=False,
                     cache_updatefn=None):
    self.cache_dir = path(cache_dir)
    self.cache_max_size = cache_max_size

    self.cache_files = {}
    for f in self.cache_dir.findpaths(type=TYPE_FILE):
      self.cache_files[f] = f.stat().st_atime

    self.cache_size = 0
    for f in self.cache_files:
      self.cache_size += f.stat().st_size

    self.cache_copy_handler = cache_copy_handler or CopyHandler()

    self.force = force # whether to force (re)downloading to cache
    self.cache_updatefn = cache_updatefn or mirror_updatefn

  def copy(self, srcfile, dstfile, callback=None, size=16*1024, seek=0.0):
    """
    Copy srcfile into dstfile, but cache the result first.  Basic algorithm is
    as follows:

     1. Check to see if the file in the cache is up to date; if it isn't, copy
        from srcfile to cshfile (a file in the cache)
     2. Copy from cshfile to dstfile

    There is some trickery involved in resuming partial copy operations, since
    an incomplete copy to the cache means that sync thinks the file wasn't
    copied at all.  Thus, we compute the location that srcfile should be opened
    at before calling our parent's copy() method.

    There is one case where cache will misbehave; however, you really have to
    try hard to ensure it happens.  The following conditions, if met, will
    result in a corrupt file in the cache:

     * A sync of a file to the cache was canceled early
     * The file in the cache was modified in some way, while remaining smaller
       than the file in the source
     * The modified time of the file in the cache was changed to match that on
       the source file

    In this case, the cache handler thinks it has an incomplete download and
    starts copying from the end of the current file.  Since it has changed,
    though, the resulting output file is not valid.  Since the second two
    conditions are Bad Practice (tm), and since this assumption allows caching
    to support partial file download resumption, this is considered an
    acceptable approach.  You can always use the force option to force a
    redownload if this ends up happening somehow.
    """
    read = seek or 0.0

    cshfile = self.cache_dir / self._gen_hash(srcfile.normpath())

    if self.force or not cshfile.exists():
      start = 0
    else:
      start = self.cache_updatefn(srcfile, cshfile)

    if callback and hasattr(callback, '_cache_start'):
      callback._cache_start(srcfile.stat().st_size, srcfile.basename)

    if start == 0:
      cshfile.rm(force=True)

    if start >= 0:
      self.cache_dir.mkdirs()
      if callback and hasattr(callback, '_notify_cache'):
        callback._notify_cache()
      try:
        CopyHandler.copy(self, srcfile, cshfile, callback=callback,
                               size=size, seek=start)
      finally:
        if cshfile.exists():
          src_st = srcfile.stat()
          cshfile.utime((src_st.st_atime, src_st.st_mtime))
          self._touch(cshfile)
          self.cache_size += cshfile.stat().st_size

    # if this method is called, we know for sure that src is newer than dst, so
    # always copy cshfile to dstfile
    if callback and hasattr(callback, '_notify_copy'):
      callback._notify_copy()
    self.cache_copy_handler.copy(cshfile, dstfile,
                                 callback=callback, size=size, seek=read)

    # enforce cache quota size
    if callback and hasattr(callback, '_cache_quota'):
      callback._cache_quota()
    self._enforce_quota(callback=callback)

    if callback and hasattr(callback, '_cache_end'):
      callback._cache_end()

  def _gen_hash(self, text):
    "Generate a hash of a filename"
    return hashlib.md5(text).hexdigest()

  def _touch(self, hash):
    "Touch a file in the cache list to update its atime"
    self.cache_files.setdefault(hash, time.time())

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


#------ CALLBACK ------#
class CachedSyncCallback(SyncCallbackMetered):
  """
  A callback for use with CachedSyncHandler.  Its primary feature is the
  consolidation of both copy operations into a single progress bar, as well
  as hiding the cached file's hash name (since it is ugly).
  """
  def __init__(self, verbose=False):
    SyncCallbackMetered.__init__(self, verbose=verbose,
      layout='%(title)-30.30s [%(bar)s] %(curvalue)5.5sB (%(time-elapsed)s)')

    self.mode = 'COPY'

  def _cache_start(self, size, text):
    self.filename = text
    self.bar = ProgressBar(self.layout, title=self.filename, size=size)
    self.bar.tags.get('curvalue').update(condense=True, ftype=str)
    self.bar.tags.get('maxvalue').update(condense=True, ftype=str)

    if not self.enabled: self.bar._fo = None

    self.bar.start()
    self.bar.join()

  def _notify_cache(self):
    self.mode = MODE_CACHE

  def _notify_copy(self):
    self.mode = MODE_COPY

  def _cp_start(self, size, text, seek=0.0):
    if self.mode == MODE_CACHE:
      self.bar.tags.get('bar').update(unfilled=' ', filled='-')
    elif self.mode == MODE_COPY:
      self.bar.tags.get('bar').update(unfilled='-', filled='=')

    self.bar.update(seek)

  def _cp_end(self, amount_read):
    # don't draw the bar; we're not finish()d yet
    pass

  def _cache_end(self):
    self.bar.update(self.bar.status.size)
    self.bar.finish() # wait for bar to finish drawing
    del self.bar

  def _cache_quota_rm(self, file, file_size, cache_size):
    pass


# convenience function
def sync(src, dst='.', strict=False, callback=None, copy_handler=None,
                       updatefn=None, cache_updatefn=None,
                       cache_copy_handler=None, **kwargs):
  so = SyncOperation(strict=strict, callback=callback or CachedSyncCallback(),
         copy_handler=copy_handler or
           CachedSyncHandler(cache_copy_handler=cache_copy_handler,
                             cache_updatefn=cache_updatefn),
         updatefn=updatefn)
  so.sync(src, dst, **kwargs)
