#
# Copyright (c) 2013
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
  """
  def __init__(self, strict=False, callback=None,  link=False, force=False,
               **kwargs):
    "Instantiate a SyncOperation object"
    self.strict = strict
    self.callback = callback or SyncCallback()
    self.link = link
    self.force = force

  def sync(self, src, dst=None, mode=None, username=None, password=None, 
                      **kwargs):
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
        self._update_existing(srcfile, dstfile, **kwargs)
      else:
        self._copy_new(srcfile, dstfile)
      if mode:
        dstfile.chmod(mode)

    if self.strict:
      self._delete_old(src, dst, srclist)

    self.callback.end(src, dst)

  def _srclist(self, src):
    """
    Compute the list of files to be copied from src.  Subclassing this method
    will allow greater control over what files to be synced.
    """
    src.stat() # trick to raise pps path error if path does not exist
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

  def _update_existing(self, srcfile, dstfile, **kwargs):
    """
    srcfile, dstfile both exist; update dstfile if any of the following are
    true:

     * srcfile differs from dstfile (srcfile.st_mtime != dstfile.st_mtime)
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

      self.callback.update(srcfile, dstfile)
      self._copy_file(srcfile, dstfile, **kwargs)

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

  def _copy_file(self, srcfile, dstfile, force=False, link=False, **kwargs):
    "Copy srcfile to dstfile."
    srcfile.cp(dstfile, callback=self.callback, 
                        link=(link or self.link),
                        force=(force or self.force),
                        mirror=True,
                        **kwargs)


# convenience function
def sync(src, dst, strict=False, callback=None, **kwargs):
  """
  Convenience function for setting up a SyncOperation and performing a sync
  in one call.

  It is slightly more efficient to use SyncOperation.sync() instead of sync()
  when performing several sync operations in a row.
  """
  so = SyncOperation(strict=strict, callback=callback, **kwargs)
  so.sync(src, dst, **kwargs)


class SyncError(OSError): pass
