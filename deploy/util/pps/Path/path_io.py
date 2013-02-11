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
import errno
import hashlib
import stat

from deploy.util.pps import path

from deploy.util.pps.lib       import cached
from deploy.util.pps.constants import *

from deploy.util.pps.Path.error import PathError

class Path_IO(object):
  "I/O operations for Path objects"

  # file metadata modification functions
  def utime(self, times):    raise NotImplementedError
  def chmod(self, mode):     raise NotImplementedError
  def chown(self, uid, gid): raise NotImplementedError
  def copymode(self, dst):
    path(dst).chmod(stat.S_IMODE(self.stat().st_mode))
  def copystat(self, dst, time=True, mode=True, owner=True):
    st = self.stat()
    dst = path(dst)
    if time:  dst.utime((st.st_atime, st.st_mtime))
    if mode:  dst.chmod(stat.S_IMODE(st.st_mode))
    if owner: dst.chown(st.st_uid, st.st_gid)

  # file/directory creation/modification
  def rename(self, new):      raise NotImplementedError
  move = rename
  def mkdir(self, mode=0777): raise NotImplementedError
  def mkdirs(self):
    """
    Algorithm method

    Makes the directory represented by this Path object.  If one or more of the
    parent directories do not exist, also makes those.
    """
    for i in range(0, len(self.splitall())):
      dirstack = self.splitall()[0:i+1]
      if not dirstack.exists():
        dirstack.mkdir()
      elif dirstack.isfile():
        raise PathError(errno.EEXIST, "cannot create directory '%s'" % self)
  def rmdir(self):            raise NotImplementedError
  def removedirs(self):
    """
    Algorithm method

    Remove the current directory, and recursively remove parent directories
    until an error is raised
    """
    try:
      self.rmdir()
      self.dirname.removedirs()
    except PathError:
      pass
  def mknod(self):  raise NotImplementedError
  def touch(self):  raise NotImplementedError
  def remove(self): raise NotImplementedError
  def unlink(self): raise NotImplementedError
  def rm(self, recursive=False, force=False):
    """
    Algorithm method

    Remove the underlying file or directory this Path object represents.  If
    recursive is enabled and the path is a directory, recursively removes its
    contents.  If force is enabled, silently fails if the path does not exist.
    """
    if self.isfile() or self.islink():
      self.remove()
    elif self.isdir():
      if not recursive and not force:
        raise PathError(errno.EISDIR, "cannot remove '%s'" % self)
      else:
        for dirs, files, level in self.walk(topdown=False, follow=False):
          for file in files: file.remove()
          for dir in dirs:
            if dir.islink(): dir.remove() # links to dirs show up in dirs list
            else:            dir.rmdir()
        self.rmdir()
    else:
      if not force:
        raise PathError(errno.ENOENT, "cannot remove '%s'" % self)

  # links
  def link(self, new):    raise NotImplementedError
  def symlink(self, new): raise NotImplementedError
  def readlink(self):     raise NotImplementedError

  # file reading, copying, writing
  def open(self): raise NotImplementedError
  def copyfile(self, dst):
    fsrc = None
    fdst = None
    try:
      fsrc = self.open('rb')
      fdst = path(dst).open('wb')
      copyfileobj(fsrc, fdst)
    finally:
      if fsrc: fsrc.close()
      if fdst: fdst.close()
  def cp(self, dst, recursive=False, preserve=False, follow=False,
                    **kwargs):
    """
    Algorithm method

    Copies the file represented by this path to the path at dst.  If
    recursive is enabled and the path is a directory, also copy all the
    directory's contents. If preserve is enabled, also copy access and
    modified time to the destionation. The keyword arguments link, force,
    and update control exactly how this copy is performed; link creates
    file links, force removes the destination before copying, and update
    only copies if the source is newer than the destination.
    """
    dst = path(dst)
    if self.isdir():
      if not recursive:
        raise PathError(errno.EISDIR, "cannot copy directory '%s' in non-recursive mode" % self)
      d = dst / self.basename
      if not d.exists():
        d.mkdirs()
        if preserve and not d.islink(): self.copystat(d)
      for dirs, files, level in self.walk(follow=follow):
        for dir in dirs:
          d = dst/self.basename/dir.splitall()[-level:]
          if not d.exists(): d.mkdir()
          if preserve and not d.islink(): dir.copystat(d)
        for file in files:
          d = dst/self.basename/file.splitall()[-level:]
          file._copy(d, **kwargs)
          if preserve and not d.islink(): file.copystat(d)
    elif self.isfile() or self.islink():
      if dst.isdir():
        d = dst / self.basename
      else:
        d = dst
      self._copy(d, **kwargs)
      if preserve and not d.islink(): self.copystat(d)
  def _copy(self, dst, force=False, link=False, update=False):
    "copy() helper function"
    dst = path(dst)
    if force:
      dst.rm(force=True)
    if update:
      if dst.exists() and (self.stat().st_mtime > dst.stat().st_mtime):
        dst.remove()
      if link: self.link(dst)
      else:    self.copyfile(dst)
    else:
      if self.islink():
        if dst.exists():
          raise PathError(errno.EEXIST, "cannot create symlink '%s'" % dst)
        self.readlink().symlink(dst)
      elif link:
        if dst.exists():
          raise PathError(errno.EEXIST, "cannot create link '%s'" % dst)
        self.link(dst)
      else:
        self.copyfile(dst)

  def read_text(self, size=-1, **kwargs):
    fo = self.open('r', **kwargs)
    try:
      return fo.read(size)
    finally:
      fo.close()

  def read_lines(self, size=-1, linesep='\n', **kwargs):
    fo = self.open('r', **kwargs)
    try:
      lines = fo.read(size).split(linesep)
      if not lines[-1]: lines = lines[:-1] # most files end with a blank newline
      return lines
    finally:
      fo.close()

  def write_text(self, bytes, append=False):
    self.write_lines([bytes], append=append, linesep='')

  def write_lines(self, lines, append=False, linesep='\n'):
    if append: fo = self.open('ab')
    else:      fo = self.open('wb')
    try:
      for line in lines:
        fo.write(line.rstrip(linesep)+linesep)
    finally:
      fo.close()

  @cached()
  @cached(globally=True)
  def checksum(self, type='sha256', hex=True):
    "Compute a checksum using mod (sha or md5).  Return the (hex)digest"
    if type == 'sha': type = 'sha1'
    mod = eval("hashlib.%s" % type)
    csum = mod(self.read_text())
    if hex: return csum.hexdigest()
    else:   return csum.digest()

def copyfileobj(fsrc, fdst, buflen=16*1024):
  "Copy from open file object fsrc to open file object fdst"
  while True:
    buf = fsrc.read(buflen)
    if not buf: break
    fdst.write(buf)
