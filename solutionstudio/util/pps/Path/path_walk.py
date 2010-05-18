#
# Copyright (c) 2007, 2008
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
import errno
import fnmatch
import re

from solutionstudio.util.pps.constants import *
from solutionstudio.util.pps.PathSet   import PathSet

from solutionstudio.util.pps.Path.error import PathError


class Path_Walk(object):
  "Path iteration/walking functions"
  def listdir(self): raise NotImplementedError

  def walk(self, maxdepth=None, topdown=True, follow=True):
    """
    Algorithm method

    dirs, files, level = self.walk()

    Return a generator for traversing down the tree starting at self.
    dirs and files are PathSet objects containing the contents of the current
    level of traversal, while level is the level in the tree beneath root of
    the walk in which these files are located.

    maxdepth controls the maximum depth in the tree the walk will recurse to.
    Any directories beneath this depth are ignored.  topdown controls whether
    to walk from the top directory down to its children or from the children
    up to the top directory.  (Some operations require the latter; for example,
    recursive removal of files and directories.)  Finally, follow controls
    the behavior of walk() with regard to symbolic links.  If True, symbolic
    links are treated as directories and followed; if False, they are
    considered files and not followed.
    """
    if not self.isdir():
      return

    for x in self._walk(maxdepth, topdown, follow):
      yield x

  def _walk(self, maxdepth=None, topdown=True, follow=True, level=0):
    if maxdepth and maxdepth <= level: return

    dirs, nondirs = [], []
    for name in self.listdir(all=True, sort=None):
      if name.isdir():
        if name.islink():
          if follow: dirs.append(name)
          else:      nondirs.append(name)
        else:
          dirs.append(name)
      else: nondirs.append(name)

    if topdown:
      if dirs or nondirs:
        yield dirs, nondirs, level+1
      else:
        yield dirs, nondirs, level

    for name in dirs:
      if ( ( name.islink() and
             (name.dirname/name.readlink()).exists() ) or
           not name.islink() ):
        for x in name._walk(maxdepth, topdown, follow, level+1):
          yield x

    if not topdown:
      if dirs or nondirs:
        yield dirs, nondirs, level+1
      else:
        yield dirs, nondirs, level

  def findpaths(self, glob=None, nglob=None, regex=None, nregex=None,
                      type=0111, mindepth=None, maxdepth=None, follow=False):
    """
    Algorithm method

    Find all paths beneath and including self.  Returns results in a FileSet.

    glob, nglob, regex, and nregex filter the results returned by findpaths().
    Globs are processed as they are seen - each path element must match glob
    and not match nglob in order to be returned in the final result.  Regexes
    are processed at the end - as with globs, each path element must match
    regex and not match nregex in order to be returned in the final result.

    type specifies the types of files that should be included in the search.
    It defaults to all file types; however, results can be filtered to show
    directories, files, and/or links (combined by performing bitwise ORing of
    the various file types as defined in constants.py).

    follow indicates whether to follow symlinks or not

    Finally, mindepth and maxdepth control which levels of the tree are
    considered for results (self is at level 0).
    """

    found = PathSet()

    if not self.exists(): return found

    # add self to list if necessary
    if ( (mindepth or 0) <= 0 and
         self.exists() and _matches(self, type, glob, nglob) ):
      found.append(self)

    # find all children
    for dirs, files, level in self.walk(maxdepth=maxdepth, follow=follow):
      if level >= (mindepth or 0):
        found.extend([ f for f in files
                       if _matches(f, type, glob, nglob) ])
        found.extend([ d for d in dirs
                       if _matches(d, type, glob, nglob) ])

    # postprocess list - match against regexes, sort
    if regex:  found.rematch(regex)               # remove items that don't match regex
    if nregex: found.rematch(nregex, invert=True) # remove items that do match nregex
    found.sort()

    return found

  def fnmatch(self, pattern):
    if isinstance(pattern, basestring): pattern = [pattern]
    for p in pattern:
      if fnmatch.fnmatchcase(self.basename, p):
        return True
    return False

  def rematch(self, pattern):
    # this method accepts both strings and already-compiled regexes
    if not hasattr(pattern, '__iter__'): pattern = [pattern]
    for p in pattern:
      if re.match(p, self) is not None:
        return True
    return False

  def glob(self, pattern=None):
    "Return a PathSet of Paths that match the glob specified in pattern"
    matches = PathSet()

    pattern = self/pattern # if pattern is None, returns self

    if not has_magic(pattern):
      if pattern.exists():
        matches.append(pattern)
      return matches

    dirname, basename = pattern.splitpath()

    if has_magic(dirname):
      dirs = self.glob(dirname)
    else:
      dirs = [dirname]

    for dir in dirs:
      for name in _glob(dir, basename):
        matches.append(dir/name)

    return matches

def _glob(dir, pattern):
  if not has_magic(pattern):
    name = (dir/pattern)
    if name.exists(): return [name]

  try:
    names = dir.listdir()
  except PathError:
    return []

  # don't include dotfiles (.xyz) if the pattern doesn't start with '.'
  if pattern[0] != '.':
    names = filter(lambda x: x.basename[0] != '.', names)

  return fnmatch.filter([ n.basename for n in names ], pattern)

magic_check = re.compile('[*?[]')
def has_magic(string):
  return magic_check.search(string) is not None

def _matches(fn, expected, glob=None, nglob=None):
  "Returns true iff fn is of the expected types, matches glob, and doesn't "
  "match nglob"
  return ( ( (expected & TYPE_DIR)  and fn.isdir()  or
             (expected & TYPE_FILE) and fn.isfile() or
             (expected & TYPE_LINK) and fn.islink() )
           and
           ( (not glob  or     fn.fnmatch(glob)) and
             (not nglob or not fn.fnmatch(nglob)) ) )
