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
"ftp.py - implementation of PathStat for ftp locations"

import stat
import time

from openprovision.util.pps.constants import *

from openprovision.util.pps.Path.error import PathError
from openprovision.util.pps.lib.ftp    import FtpFileObject

from remote import RemotePathStat

COLUMNS = ['mode', 'nlink', 'uid', 'gid', 'size', 'month', 'day', 'year', 'path']

class FtpPathStat(RemotePathStat):
  """
  FtpPathStat fully implements the PathStat interface.  However, some of
  the fields present in a normal PathStat result are meaningless or
  impossible to determine on ftp locations.  These include st_ctime,
  st_dev, and st_ino, they are represented by -1 in the resulting tuple.
  """
  def stat(self, fo=None):
    """
    FtpPathStat's stat() call allows passing a file object in the fo
    argument, which can be an open file-like object on the file located
    at FtpPathStat.uri. This allows a slight bit of optimization by
    minimizing FTP requests made on the server.  If fo is None,
    FtpPathStat creates its own connection.
    """
    if not fo:
      stat_fo = FtpFileObject(self.uri)
    else:
      stat_fo = fo

    # try a series of stuff to figure out the stat result
    try:
      mode, nlink, uid, gid, size, _,_,_ = self._best_stat(stat_fo)
      mode  = statfmt.deformat(mode) # convert mode string into an int
      if stat.S_IFDIR(mode):
        mtime = -1
      else:
        mtime = _parse_mdtm(stat_fo.ftp.ftp.sendcmd('MDTM %s' % self.uri.basename))
    except Exception, e:
      print e
      mode, nlink, uid, gid, size, mtime = self._slow_stat(stat_fo)

    nlink = int(nlink)
    size  = int(size)
    # sometimes these return strings, which aren't valid in stat results
    try:    uid = int(uid)
    except: uid = -1
    try:    gid = int(gid)
    except: gid = -1

    # if we weren't passed a file object, close the one we created
    if not fo: stat_fo.close()

    # set atime
    atime = int(time.time())

    self._stat = list((mode, -1, -1, nlink, uid, gid, size, atime, mtime, -1))

  def _best_stat(self, fo):
    "Fastest way to get stat results"
    dir_result = []
    fo.ftp.ftp.dir(self.uri.dirname, dir_result.append)
    dirparse = _parse_dir(dir_result, COLUMNS)
    if not dirparse:
      raise PathError(2, "No such file or directory", self.uri)
    ## set other stat caches up here to save time!
    return dirparse[self.uri.basename]

  def _slow_stat(self, fo):
    "Slower stat method, less information as well"
    try:
      size  = fo.ftp.ftp.size(self.uri.basename)
      mode  = stat.S_IFREG
      mtime = []
      fo.ftp.ftp.sendcmd('MDTM %s' % self.uri.basename, mtime.append)
      mtime = _parse_mdtm(mtime[0])
    except Exception, e:
      if not fo.ftp.ftp.nlst(self.uri.basename):
        raise PathError(2, "No such file or directory", self.uri)
      # can't get size/mtime on directories, so its a directory!
      size  = -1
      mode  = stat.S_IFDIR
      mtime = -1

    return mode, -1, -1, -1, size, mtime

def _parse_mdtm(s):
  "Ftp servers return odd representations of mtime..."
  _,mdtm = s.split() # response code 221, mdtm
  return int(time.mktime(time.strptime(mdtm, '%Y%m%d%H%M%S')))

def _parse_dir(lines, cols):
  "Parse the result of calling dir on a FtpFileObject"
  r = {}

  # split and assign data based on index
  for line in lines:
    vs = line.split()
    assert len(vs) == len(cols)
    data, k = vs[:-1], vs[-1]
    r[k] = tuple(data)

  return r
