#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
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

from math import ceil, log

from centosstudio.util.pps            import path
from centosstudio.util.pps.Path.error import PathError

from centosstudio.util.pps.Path.remote import RemotePath #!

# list of error codes that indicate that we were unable to get files from
# a host because of problems with the host itself: name or service unknown,
# host unreachable, etc
# its highly unlikely that this is the full list of errors we need
# to except, so more additions will come
HOSTUNAVAIL = [ errno.ETIMEDOUT, errno.ECONNREFUSED,  # 110, 111
                errno.EHOSTDOWN, errno.EHOSTUNREACH ] # 112, 113

# decorator for mirroring
def trymirrors(meth):
  # meth should raise ContinueIteration to try the next mirror or
  # StopIteration to indicate it is done checking mirrors.
  def new(self, *args, **kwargs):
    self.mirrorgroup.reset()
    # number of times to fail before accepting the result - allows for use
    # of non-perfect mirrors
    num_fails = int(ceil(log(len(self.mirrorgroup)+1)))
    faildata = [] # list of errors accumulated
    try:
      while True:
        mi = self.mirrorgroup.next()
        try:
          try:
            return meth(self, mi//self.path, *args, **kwargs)
          except PathError, e:
            if e.errno in HOSTUNAVAIL:
              self.mirrorgroup.disable_mirror() # disable failed mirror
              continue
            else:
              faildata.append(e)
              # if we've failed num_fails times or once for every mirror in
              # the mirrorgroup, raise a MirrorPathError with failure details
              if ( len(faildata) >= min(num_fails, len(self.mirrorgroup)) ):
                raise MirrorPathError(self, faildata)
              continue
        except ContinueIteration, e:
          if e.err:
            self.mirrorgroup.disable_mirror() # disable failed mirror
          continue
        except StopIteration:
          return

    except NoMoreMirrors:
      # ENOENT is kind of right, but not really
      raise PathError(errno.ENOENT, "No more mirrors to try: '%s'" % self.path,
                      'Resource unavailable')

  return new

class MirrorGroup(list):
  def __init__(self, iterable):
    # create list, filtering out unsupported items
    list.__init__(self, [ [path(x), True] for x in
                          filter(self._filter, iterable) ])

    # hack - reduce the timeout on remote mirrorlist items and only try once
    for mi in self: #!
      if isinstance(mi, RemotePath): #!
        mi._foargs.update(dict(retries=1, timeout=5)) #!

    self._current = -1 # index of current mirror

  @classmethod
  def _filter(cls, item):
    "Return False for items we don't want in our mirror list"
    return (
      not item.startswith('ftp') and # pps doesn't currently support ftp #!
      not item.startswith('#') and   # comment
      not item.startswith('<') and   # probably html
      not item.startswith(' ') and   # probably invalid (often html)
      not item == ''                 # empty
    )

  def next(self):
    # subclass and override this method if different behavior is desired
    self._current += 1

    while self._current < len(self):
      mi, enabled = self[self._current]
      if enabled:
        return mi
      self._current += 1

    raise NoMoreMirrors()

  def reset(self):
   self._current = -1

  def get_mirror(self, i=None):
    "Get the mirror at index i, or the current mirror if i is None"
    if i is None: i = self._current
    if i == -1: return None
    else:       return self[i][0]

  def enable_mirror(self, i=None):
    "Enable the mirror at index i, or the current mirror if i is None"
    self._change_mirror_status(i, True)

  def disable_mirror(self, i=None):
    "Disable the mirror at index i, or the current mirror if i is None"
    self._change_mirror_status(i, False)

  def _change_mirror_status(self, i, status):
    if i is None: i = self._current
    if i == -1: return # don't try to disable with no current mirror
    else:       self[i][1] = status


def validate_mirrorlist(lines):
  # validate mirrorlist to ensure its in the correct format

  # check mirrorlist to see if it lookes like html
  html = ['<html', '<!doctype html']
  line = lines[0].lower()
  for start in html:
    if line.startswith(start):
      raise MirrorlistFormatInvalidError(lines[0], 1, 'appears to be html')

  return lines

class ContinueIteration(Exception): # analog to StopIteration
  def __init__(self, err=True):
    self.err = err # whether this exception was the result of an error or not
    Exception.__init__(self)

class NoMoreMirrors(StopIteration): pass

class MirrorPathError(PathError):
  def __init__(self, path, errors):
    # path must be a pps mirrorgroup path
    if len(errors) == 1:
      # pretend like we're a normal path
      PathError.__init__(self, errors[0].errno, path.mirrorgroup[0][0]/path.path, errors[0].strerror)
    else:
      PathError.__init__(self, errors[0].errno, path, errors[0].strerror)
    self.errors = errors

  def strerrors(self):
    s = 'Tried %d mirrors; errors were:' % len(self.errors)
    for err in self.errors:
      s += '\n  %s' % err
    return s

  def __str__(self):
    if len(self.errors) == 1:
      return PathError.__str__(self)
    else:
      return '[Errno %d]: %s: %s' % (self.errno, self.strerror, self.strerrors())

class MirrorlistFormatInvalidError(ValueError):
  def __init__(self, line, lineno, reason=None):
    self.line = line
    self.lineno = lineno
    self.reason = reason

  def __str__(self):
    str = 'Mirrorlist format invalid on line %d: \'%s\'' % (self.lineno, self.line)
    if self.reason:
      str += ': %s' % self.reason
    return str
