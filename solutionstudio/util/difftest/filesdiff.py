#
# Copyright (c) 2010
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
from solutionstudio.util import pps
from solutionstudio.util import rxml
from solutionstudio.util import statfmt

NEW = '-'
NONE = '<not found>'

def diff(oldstats, newstats):
  """
  Return a dictionary of 'diff tuples' expressing the differences between
  olddata and newdata.  If there are no differences, the dictionary will be
  empty.  olddata is an expanded list of dictionaries containing 'size',
  'mtime', and 'mode' values; newdata is a list of lists of filenames.

  There are 3 possible types of diff tuples.  Each means something slightly
  different:
    (size, mtime, mode):
      in metadata: file is present in metadata file
      in struct:   file is listed in struct and exists on disk
    (None, None, None):
      in metadata: N/A
      in struct:   file is listed in struct but does not exist
    None:
      in metadata: file is not present in metadata file
      in struct:   file is not listed in struct
  """
  diffdict = FilesDiffDict()

  # keep a list of already-processed elements so we don't add them in twice
  processed = []

  # first check for presence/absence of files in each list
  for x in newstats:
    if x not in oldstats:
      diffdict[x] = (None, newstats[x])
      processed.append(x)

  for x in oldstats:
    if x not in newstats:
      diffdict[x] = (oldstats[x], None)
      processed.append(x)

  # now check sizes, mtimes and modes
  for file in oldstats:
    if file in processed: continue
    if oldstats[file] != newstats[file]:
      diffdict[file] = (oldstats[file], newstats[file])
  return diffdict

class DiffTuple:

  attrs = [('size', int), ('mtime', int), ('mode', int)]

  def __init__(self, path=None):
    self.path = pps.path(path)

    self.size  = None
    self.mtime = None
    self.mode  = None

    if self.path:
      try:
        st = self.path.stat()
        self.size  = st.st_size
        self.mtime = st.st_mtime
        self.mode  = st.st_mode
      except pps.Path.error.PathError:
        pass
    else:
      pass

  # pretend to be a tuple
  def __repr__(self): return repr(tuple(self.values()))
  def __str__(self):  return str(tuple(self.values()))

  def __ne__(self, other): return not self.__eq__(other)
  def __eq__(self, other):
    if self.keys() != other.keys(): return False

    for k,v in self.items():
      if getattr(self, k) != getattr(other, k):
        return False

    return True

  def keys(self):
    return [ k for k,v in self.items() ]

  def values(self):
    return [ v for k,v in self.items() ]

  def items(self):
    return [ (k[0], getattr(self, k[0], None)) for k in self.attrs ]

  def toxml(self):
    e = rxml.config.Element('file', attrs={'path': self.path})
    for k,v in self.items():
      if v is not None: rxml.config.Element(k, parent=e, text=str(v))
      else: rxml.config.Element(k, parent=e)
    return e

  def fromxml(self, xml):
    self.path = xml.get('@path')
    for key,fn in self.attrs:
      if xml.pathexists('%s/text()' % key):
        setattr(self, key, fn(xml.get('%s/text()' % key)))
      else:
        setattr(self, key, None)
    return self

  def diff(self, other):
    D = []

    if not other:
      for attr in self.keys():
        D.append((attr, getattr(self, attr), NEW))
      return D

    for attr in self.keys():
      if attr not in other.keys():
        D.append((attr, getattr(self, attr), NONE))
      else:
        if getattr(self, attr) != getattr(other, attr):
          D.append((attr, getattr(self, attr), getattr(other, attr)))

    for attr in other.keys():
      if attr in self.keys(): continue
      D.append((attr, NONE, getattr(other, attr)))

    ##if D: print self.path, self, other

    return D


class FilesDiffDict(dict):
  def __repr__(self): return dict.__repr__(self)
  def __str__(self):
    s = ''

    for key, filetup in self.items():
      s += key + '\n'
      s += '%s%12.12s%12.12s\n' % (' '*9, 'Metadata', 'Disk')

      metadata, disk = filetup

      assert (metadata or disk)

      if metadata:
        D = metadata.diff(disk); invert = False
      else:
        D = disk.diff(metadata); invert = True

      for key, v1, v2 in D:
        key = '  %s' % key
        if invert:
          s += '%-9.9s%12.12s%12.12s\n' % (key, v1, v2)
        else:
          s += '%-9.9s%12.12s%12.12s\n' % (key, v2, v1)

    return s

