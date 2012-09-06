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

from repostudio.util.pps.lib.mirror import trymirrors

from repostudio.util.pps.Path.remote import RemotePath_IO

class MirrorPath_IO(RemotePath_IO):

  # file metadata modification
  @trymirrors
  def utime(self, f, *a,**kw):    return f.utime(*a,**kw)
  @trymirrors
  def chmod(self, f, *a,**kw):    return f.chmod(*a,**kw)
  @trymirrors
  def chown(self, f, *a,**kw):    return f.chown(*a,**kw)
  @trymirrors
  def copymode(self, f, *a,**kw): return f.copymode(*a,**kw)
  @trymirrors
  def copystat(self, f, *a,**kw): return f.copystat(*a,**kw)

  # file/directory creation/modification
  @trymirrors
  def rename(self, f, *a,**kw):   return f.rename(*a, **kw)
  @trymirrors
  def mkdir(self, f, *a,**kw):    return f.mkdir(*a,**kw)
  @trymirrors
  def mkdirs(self, f, *a,**kw):   return f.mkdirs(*a,**kw)
  @trymirrors
  def rmdir(self, f, *a,**kw):    return f.rmdir(*a,**kw)
  @trymirrors
  def removedirs(self, f, *a,**kw): return f.removedirs(*a,**kw)
  @trymirrors
  def mknod(self, f, *a,**kw):    return f.mknod(*a,**kw)
  @trymirrors
  def touch(self, f, *a,**kw):    return f.touch(*a,**kw)
  @trymirrors
  def remove(self, f, *a,**kw):   return f.remove(*a,**kw)
  @trymirrors
  def unlink(self, f, *a,**kw):   return f.unlink(*a,**kw)
  @trymirrors
  def rm(self, f, *a,**kw):       return f.rm(*a,**kw)
  @trymirrors
  def link(self, f, *a,**kw):     return f.link(*a,**kw)
  @trymirrors
  def symlink(self, f, *a,**kw):  return f.symlink(*a,**kw)
  @trymirrors
  def readlink(self, f, *a,**kw): return f.readlink(*a,**kw)

  # file reading, copying, writing
  @trymirrors
  def open(self, f, *a,**kw):        return f.open(*a,**kw)
  @trymirrors
  def copyfile(self, f, *a,**kw):    return f.copyfile(*a,**kw)
  @trymirrors
  def cp(self, f, dst, *a,**kw):     return f.cp(dst, *a,**kw)
  @trymirrors
  def read_text(self, f, *a,**kw):   return f.read_text(*a,**kw)
  @trymirrors
  def read_lines(self, f, *a,**kw):  return f.read_lines(*a,**kw)
  @trymirrors
  def write_text(self, f, *a,**kw):  return f.write_text(*a, **kw)
  @trymirrors
  def write_lines(self, f, *a,**kw): return f.write_lines(*a, **kw)
