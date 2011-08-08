#
# Copyright (c) 2011
# OpenProvision, Inc. All rights reserved.
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
import os
import shutil

from openprovision.util import pps
from openprovision.util import shlib

from openprovision.util.img import acquire_mount_point, release_mount_point, MODES, MODE_READ, MODE_WRITE
from openprovision.util.img.errors import *

class Image:
  def __init__(self, image, zipped=False):
    image = pps.path(image)
    if not image.exists():
      raise ImageIOError, "The image file '%s' does not exist" % image

    self.name = image.basename
    self.imgfile = image.realpath()
    self.imgloc = self.imgfile # this gets modified if the file(s) we're working on move
    self.mode = None

    self.compress = zipped # zip property, is this image zipped when closed?
    self.stat = None # location to store stat result before/after opening/closing
    self.changed = False # whether image has changed since opening

    self.zipped = self.compress # zip status, is this image zipped now?
    self.closed = True
    self.size   = None # initialized by getsize()
    self.capacity = None # -1 for images that have no capacity, initialized by getcapacity()

    self.handler = None # the image file type handler

  def unzip(self):
    "Unzip the image"
    if self.zipped:
      newloc = acquire_mount_point()/self.name
      shlib.execute('gunzip -c %s > %s' % (self.imgfile, newloc))
      self.imgloc = newloc
      self.zipped = False
    else:
      raise ImageIOError, ERROR_NOT_ZIPPED

  def zip(self):
    "Zip the image"
    if not self.zipped:
      try:
        shlib.execute('gzip -c %s > %s' % (self.imgloc, self.imgfile))
      except:
        self.imgfile.rm(force=True)
        raise
      release_mount_point(self.imgloc.dirname)
      self.imgloc = self.imgfile
      self.zipped = True
    else:
      raise ImageIOError(ERROR_ZIPPED)

  def getsize(self):
    if self.closed:
      raise ImageIOError(ERROR_GETSIZE % 'image is closed')
    self.size = self.handler.getsize()
    return self.size

  def getcapacity(self):
    if self.zipped:
      raise ImageIOError(ERROR_GETCAPACITY % 'image is zipped')
    self.capacity = self.handler.getcapacity()
    return self.capacity

  def open(self, mode=MODE_WRITE, point=None):
    if not self.closed:
      raise ImageIOError(ERROR_ALREADY_OPEN)
    if mode not in MODES:
      raise ValueError("Unsupported mode '%s'" % mode)

    self.stat = self.imgloc.stat()

    if self.compress: self.unzip()
    self.handler.open(mode, point)
    self.mode = mode
    self.closed = False
    self.getsize()
    self.getcapacity()

  def close(self):
    if self.closed:
      raise ImageIOError, ERROR_ALREADY_CLOSED

    self.getsize()
    self.getcapacity()

    self.handler.close()

    if self.compress: self.zip()

    # make sure file metadata (owner, group, permissions, times, etc) is unchanged
    if self.mode == MODE_READ or not self.changed: # atime, mtime
      self.imgloc.utime((self.stat.st_atime, self.stat.st_mtime))
    # the timestamp of ext2 and fat images do not change even if their contents
    # have changed. This could be the doing of the 'mount' and 'umount' commands.
    elif self.mode == MODE_WRITE and self.changed:
      self.imgloc.touch()
    self.imgloc.chmod(self.stat.st_mode & 0777)
    self.imgloc.chown(self.stat.st_uid, self.stat.st_gid)

    self.mode = None
    self.closed = True
    self.changed = False

  def flush(self):
    if self.closed:
      raise ImageIOError(ERROR_FLUSH % 'image is closed')
    self.handler.flush()

  def write(self, src, dst='/'):
    if self.closed:
      raise ImageIOError(ERROR_WRITE % 'image is closed')
    if self.mode == MODE_READ:
      raise ImageIOError(ERROR_WRITE % 'opened in read mode')

    if not hasattr(src, '__iter__'): src = [src]

    if len(src) == 0: return

    self.handler.write([ pps.path(s) for s in src ], pps.path(dst))

    self.getsize() # update size
    self.changed = True

  def writeflo(self, fsrc, filename, dst='/'):
    "hack method of writing a file like object"
    point = acquire_mount_point()
    src = point/filename
    src.mknod()

    fdst = src.open('w')
    shutil.copyfileobj(fsrc, fdst)
    fdst.close()

    try:
      self.write(src, dst)
    finally:
      release_mount_point(point)

  def read(self, f, dst='.'):
    "read a file out of the image into dst"
    f = pps.path(f); dst = pps.path(dst)
    fsrc = self.readflo(f)
    dst.mkdirs()
    dstfile = dst/f.basename
    if not dstfile.exists(): dstfile.mknod()
    fdst = dstfile.open('w')
    shutil.copyfileobj(fsrc, fdst)
    fsrc.close()
    fdst.close()
    return dstfile

  def readflo(self, fo):
    if self.closed:
      raise ImageIOError(ERROR_READ % 'image is closed')

    return self.handler.read(fo)

  def copy(self, image1, image2):
    "copy contents of image1 into image2"
    if image1.closed:
      raise ImageIOError(ERROR_COPY % 'source image is closed')
    if image2.closed:
      raise ImageIOError(ERROR_COPY % 'destination image is closed')

    self.handler.copy(image1, image2)

  def copyto(self, image):
    "Copy the contents of self into image"
    self.copy(self, image)

  def copyfrom(self, image):
    "Copy the contents of image into self"
    self.copy(image, self)

  def remove(self, f):
    "Remove a file from the image"
    if self.closed:
      raise ImageIOError(ERROR_REMOVE % 'image is closed')
    if self.mode == MODE_READ:
      raise ImageIOError(ERROR_REMOVE % 'opened in read mode')

    if f.lstrip('/') not in self.list(relative=True):
      raise ImageIOError(ERROR_REMOVE % 'file does not exist')

    self.handler.remove(pps.path(f))

  def list(self, relative=False):
    if self.closed:
      raise ImageIOError(ERROR_LIST % 'image is closed')
    list = self.handler.list(relative=relative)
    list.sort()
    return list
