#
# Copyright (c) 2012
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
sync

Extensible file synchronization framework.  Provides the base classes and
infrastructure to perform synchronization between a variety of protocols.

This is the third complete rewrite of the sync back end.
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftare.com>'
__version__ = '0.9'
__date__    = 'April 30th, 2008'

from deploy.util import pps

from deploy.util.sync.callback import SyncCallback

class SyncOperation:
  """
  Base class representing a sync operation; allows one or more files to be
  synchronized from a source to a destination.  SyncOperations are defined by
  their treatment of the data they're synchronizing, as defined in the
  following class variables:
   * strict:       'strict syncing' is the concept of synchronizing two
                   folders so that they are completely identical;
                   specificically, strict syncing deletes any files in the
                   destination that were not present in the source
   * callback:     an object supporting callback functions at various points
                   during the sync process.  See callback.py for more
                   information
   * copy_handler: a handler that defines what exactly sync does when syncing
                   two files.  This handler is passed an open file-like object
                   for both the source and destination; in the simplest case,
                   the source is merely copied directly into the destination.
                   However, by setting the copy_handler to some other class
                   that implements the same interface, additional/alternate
                   behavior can be defined.
   * updatefn:     a function accepting two arguments, a src and dst file.
                   This function should return an integer, r, which has the
                   following meanings:
                     r >  0 : resume a partially completed download starting
                              from byte r
                     r == 0 : start a new download from the beginning
                     r <  0 : do not download anything
   * default_mode: the default mode to use when a given source file does not
                   appear to have one (00000), such as is the case with most
                   remote pps paths.  If you really do want to preserve an
                   empty mode list, set this to 0.
  """
  def __init__(self, strict=False, callback=None, copy_handler=None,
                     updatefn=None, default_mode=0644):
    "Instantiate a SyncOperation object"
    self.strict = strict
    self.callback = callback or SyncCallback()
    self.copy_handler = copy_handler or CopyHandler()
    self.updatefn = updatefn or sync_updatefn
    self.default_mode = default_mode

  def sync(self, src, dst=None, force=False, mode=None,
                      username=None, password=None):
    """
    Synchronize one or more items from src to dst.  src can be a single URI, or
    a list of URIs; dest must (currently) be a single URI.

    This is a one way sync operation (perhaps more accurately referred to as
    'mirroring').  src and dest should be include a protocol specification like
    'http' or 'file' which is separated from the path to the file by '://'.  If
    no protocol is given, 'file' is assumed.

    The basic sync() process is as follows:
     1. generate file lists for the src and dst
     2. compare the above file lists to find the files only in src, the files
        only in dst, and the files in both locations
     3. update or finish copying the files in both locations
     4. copy the files only in src
     5. if strict sync is enabled, remove the files only in dst

    If force is enabled, all files found in both locations are recopied, even if
    their timestamp indicates that the file has not changed.

    username and password can be used to pass authentication information to the
    source location, if necessary.  Alternatively, username and password can be
    included directly in the URI for URIs that support this method (http URLs,
    for example).
    """
    src = pps.path(src)
    dst = pps.path(dst or '.')

    if username and password and hasattr(src, 'set_auth'):
      src.set_auth(username, password)

    self.callback.start(src, dst)

    # The following code will change somewhat when Path objects begin returning
    # iterators instead of lists - this will allow us to traverse the tree at the
    # same time as we're performing the sync.  Hopefully, in the case of remote
    # files, this will allow us to keep an open connection to the file, minimizing
    # the number of extra remote calls
    srclist = self._srclist(src)
    dstlist = [ self._compute_dst(s.relpathfrom(src.dirname), dst)
                for s in srclist ]

    assert len(srclist) == len(dstlist)

    for srcfile, dstfile in zip(srclist, dstlist):
      if dstfile.exists():
        self._update_existing(srcfile, dstfile, force=force)
      else:
        self._copy_new(srcfile, dstfile)
      self._chmod_file(srcfile, dstfile, mode=mode)

    if self.strict:
      self._delete_old(src, dst, srclist)

    self.callback.end(src, dst)

  def _srclist(self, src):
    """
    Compute the list of files to be copied from src.  Subclassing this method
    will allow greater control over what files to be synced.
    """
    return src.findpaths()

  def _compute_dst(self, src, dst):
    """
    Compute the full destination path of a file based on src and dst.  src
    is a relative path; dst may be relative or absolute.
    """
    if dst.exists():
      if dst.isdir():
        # src = a/b/c dst = /out; return /out/a/b/c (move 'a' into 'out')        return (dst/src).normpath()
        return (dst//src).normpath()
      else:
        # src = a/b/c dst = /out; return /out/b/c (rename 'a' to 'out')
        return (dst//src.splitall()[1:]).normpath()
    elif dst.dirname.exists():
      # src = a/b/c dst = /out; return = /out/b/c (rename 'a' to 'out')
      return (dst//src.splitall()[1:]).normpath()
    else:
      raise SyncError("cannot sync '%s' into '%s'; destination does not exist" % (src, dst))

  def _update_existing(self, srcfile, dstfile, force=False):
    """
    srcfile, dstfile both exist; update dstfile any of the following are true:

     * srcfile is newer than dstfile (srcfile.st_mtime >  dstfile.st_mtime)
     * srcfile is an incomplete download of dstfile (srcfile.st_mtime ==
       dstfile.st_mtime and srcfile.st_size < dst.st_size)
     * force is True

    Errors if srcfile and dstfile type doesn't match (file/directory) and
    force is not enabled.
    """
    # source is a directory
    if srcfile.isdir():
      if dstfile.isfile():
        if self.strict:
          dstfile.rm()
          dstfile.mkdir()
        else:
          raise SyncError("cannot sync directory '%s' over '%s': not a directory" % (srcfile, dstfile))
    # source is a file
    elif srcfile.isfile():
      if dstfile.isdir():
        if self.strict:
          dstfile.rm(recursive=True)
        else:
          raise SyncError("cannot sync file '%s' over '%s': is a directory" % (srcfile, dstfile))

      if force: seek = 0
      else:     seek = self.updatefn(srcfile, dstfile)

      # interpret the result of self.updatefn()
      if seek < 0:
        # we're done
        return
      elif seek == 0:
        # download new files from the beginning
        dstfile.rm()
        self.callback.update(srcfile, dstfile)
        self._copy_file(srcfile, dstfile)
      else:
        # resume partially-completed download
        self.callback.cp(srcfile, dstfile)
        self._copy_file(srcfile, dstfile, seek=seek)

  def _copy_new(self, srcfile, dstfile):
    """
    srcfile exists, dstfile does not; dstfile.dirname exists

    Creates a directory named dstfile if srcfile is a directory; copies
    srcfile into dstfile if srcfile is a file.
    """
    # source is a directory
    if srcfile.isdir():
      self.callback.mkdir(srcfile, dstfile)
      dstfile.mkdir()
    # source is a file
    elif srcfile.isfile():
      self.callback.cp(srcfile, dstfile)
      self._copy_file(srcfile, dstfile)

  def _delete_old(self, src, dst, srclist):
    """
    Delete the files in dst that are not in srclist.
    """
    for f in (
        set([ d.relpathfrom(dst) for d in dst.findpaths(mindepth=1) ]) -
        set([ s.relpathfrom(src.dirname) for s in srclist ]) ):
      self.callback.rm(f)
      f.rm(recursive=True, force=True)

  def _copy_file(self, srcfile, dstfile, seek=None):
    """
    Copy srcfile to dstfile.  If seek is not None, start copying from seek in
    srcfile instead of from 0.
    """
    try:
      self.copy_handler.copy(srcfile, dstfile, callback=self.callback, seek=seek)
    finally:
      # update mtime
      if dstfile.exists():
        src_st = srcfile.stat()
        dstfile.utime((src_st.st_atime, src_st.st_mtime))

  def _chmod_file(self, srcfile, dstfile, mode=None):
    """
    Update the mode on the dstfile to match the mode of the srcfile or the mode
    argument, if given.
    """
    if mode is None:
      mode = (srcfile.stat().st_mode or self.default_mode) & 07777
    dstfile.chmod(mode)


#------ COPY HANDLER ------#
class CopyHandler:
  """
  Default copy handler; merely copies from fsrc to fdst

  This class can be subclassed in order to modify the default sync behavior.
  For examples of this, see CachedSyncHandler in cache.py or LinkHandler in
  link.py.
  """

  def copy(self, srcfile, dstfile, callback=None, size=16*1024, seek=0.0):
    """
    Copy from fsrc to fdst.  copy() accepts the following parameters:
     * srcfile: the full filename of the source file
     * dstfile: the full filename of the destination file
     * callback: a callback object that supports _cp_start(size, filename),
                _cp_update(amount_read), and _cp_end() methods to indicate
                copy progress; defaults to None
     * size:    the size of the copy buffer to use; defaults to 16KB
     * seek:    the position from where to start copying; defaults to 0.0
    """
    # callback start
    if callback: callback._cp_start(srcfile.stat().st_size,
                                    srcfile.basename,
                                    seek=seek or 0.0)

    fsrc = None
    fdst = None

    try:
      fsrc = srcfile.open('rb', seek=seek)
      fdst = dstfile.open('ab')

      # perform copying
      read = seek or 0.0
      while True:
        buf = fsrc.read(size)
        if not buf: break
        fdst.write(buf)
        read += len(buf)

        # callback update
        if callback: callback._cp_update(read)

    finally:
      if fsrc: fsrc.close()
      if fdst: fdst.close()

    # callback end
    if callback: callback._cp_end(read)


def sync_updatefn(src, dst):
  "Default sync behavior - update dst unless its mtime is greater than src"
  s = src.stat(); d = dst.stat()
  if s.st_mtime > d.st_mtime:
    return 0
  elif s.st_mtime == d.st_mtime and s.st_size > d.st_size:
    return d.st_size
  else:
    return -1

def mirror_updatefn(src, dst):
  "Make src and dst exactly equal copies of one another"
  s = src.stat(); d = dst.stat()
  if s.st_mtime != d.st_mtime or s.st_size < d.st_size:
    return 0
  elif s.st_mtime == d.st_mtime and s.st_size > d.st_size:
    return d.st_size
  else:
    return -1

# convenience function
def sync(src, dst, strict=False, callback=None, copy_handler=None,
                   updatefn=None, **kwargs):
  """
  Convenience function for setting up a SyncOperation and performing a sync
  in one call.

  It is slightly more efficient to use SyncOperation.sync() instead of sync()
  when performing several sync operations in a row.
  """
  so = SyncOperation(strict=strict, callback=callback, updatefn=updatefn,
                     copy_handler=copy_handler)
  so.sync(src, dst, **kwargs)


class SyncError(OSError): pass
