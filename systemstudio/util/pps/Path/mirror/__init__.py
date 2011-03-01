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
mirror - a group of Path objects that behaves like a yum mirrorgroup;
that is, all io/stat operations fail over to subsequent mirror items.

The mirror group URI syntax is as follows:

mirror:<uri of mirror>::/path/to/file

so for example:

mirror:http://mirrors.fedoraproject.org/mirrorlist?arch=i386&distro=fedora8::/repodata/repomd.xml
"""

import errno
import posixpath

from systemstudio.util.pps            import path as _path, register_scheme
from systemstudio.util.pps.UriTuple   import UriTuple
from systemstudio.util.pps.lib        import cached
from systemstudio.util.pps.lib.mirror import MirrorGroup, validate_mirrorlist
from systemstudio.util.pps.util       import urlparse, urlunparse
from systemstudio.util.pps.Path.error import PathError

from systemstudio.util.pps.Path.remote import _RemotePath as RemotePath
from systemstudio.util.pps.Path.remote import RemotePath_Printf as MirrorPath_Printf

from path_io   import MirrorPath_IO
from path_stat import MirrorPath_Stat
from path_walk import MirrorPath_Walk


mgcache = {} # cache of mirror groups

class MirrorPath(MirrorPath_IO, MirrorPath_Printf, MirrorPath_Stat,
                 MirrorPath_Walk, RemotePath):

  _pypath = posixpath # treat like posix paths

  def _splitmirror(self):
    # possible path patterns
    #  'mirror:<path to mirror>' (absolute)
    #  'mirror:<path to mirror>::<path>' (absolute)
    #  '<path>' (relative)
    # path to mirror is any valid path (including other mirrors?) - it
    # may contain '::' (in the password, for example)
    parts = self.rsplit('::', 1)

    if len(parts) == 1: # no '::' in url
      subparts = self.split(':', 1)
      if len(subparts) == 1: # relative path
        return None, None, self.__str__()
      else: # absolute path, no path specified so assume '/'
        return subparts[0], subparts[1], '/'
    elif len(parts) == 2:
      # check to make sure we didn't split a password
      subparts = parts[0].split(':', 1)
      if '@' in parts[1]:
        return subparts[0], '::'.join([subparts[1]]+parts[1:]), '/'
      else:
        return subparts[0], subparts[1], parts[1] or '/'

  @cached()
  def _urlparse(self):
    protocol,root,relpath = self._splitmirror()
    s,n,rp,p,q,f = urlparse(relpath) # s, n always None or ''
    if protocol and root:
      return UriTuple(('mirror',
                       _path(root),
                       self.__class__(relpath),
                       p, q, f))
    else:
      return UriTuple(('', '', rp, p, q, f))

  def normcase(self):
    if self.root:
      return self.__class__('%s:%s::%s' %
        (self.protocol.lower(),
         self.realm.normcase(),
         self.path or self._pypath.sep))
    else:
      return self.__class__(self._pypath.normcase(self.path))

  def normpath(self):
    if self.root:
      if self.path:
        return self.root // self._pypath.normpath(self.path)
      else:
        return self.root
    else:
      return self.__class__(self._pypath.normpath(self.path))

  def splitroot(self):
    if ( self._urlparse().path.startswith(self._pypath.sep) and
         (self.protocol and self.realm) ):
        root = self.__class__('%s:%s::/' % (self.protocol, self.realm))
        path = self.__class__(self._urlparse().path.lstrip(self._pypath.sep))
        return root, path
    else:
      return self.__class__(''), self.__class__(self._urlparse().path)

  @property
  @cached()
  def mirrorgroup(self):
    key = self.root
    if not mgcache.has_key(key):
      try:
        mg = MirrorGroup(validate_mirrorlist(self.realm.read_lines()))
      except PathError:
        raise PathError(errno.EHOSTUNREACH, self.realm,
                        'Mirrorlist unreachable')
      if len(mg) == 0:
        raise MirrorlistEmptyError(self)
      mgcache[key] = mg
    return mgcache[key]

  def touri(self):
    # think about this...
    return self.__class__(self)
    #raise ValueError("MirrorPaths cannot be converted into a valid URI")

class MirrorlistEmptyError(ValueError):
  def __init__(self, filename):
    self.errno = errno.ENODATA
    self.strerror = 'Mirrorlist exists, but empty or invalid'
    self.filename = filename

def path(string):
  return MirrorPath(string)

register_scheme('mirror', path)
