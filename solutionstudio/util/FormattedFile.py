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
"""
FormattedFile.py

A simple set of data structures designed to represent a file of known length and format.

Defines a FormattedFile object, which is essentially a (ordered) dictionary of FormattedLine
objects.  Intended usage is for representing files of known format; can be used as a
map to assist in reading values or as a template for writing out a file.
"""

import re

from rendition import pps

FMT_FIND = re.compile('%\(([^\)]+)\).') # finds %(<key>)<N>

class FormattedFile(dict):
  """A formatted file class consisting of a set number of lines of some format.
  A FormattedFile can be indexed based on line number or line name.  Note that if
  a line is named the same as a line number, the number will take precedence."""

  def __init__(self, size):
    "Creates a FormattedFile object with size lines."
    self._positions = [None] * size # order of lines

  def __getitem__(self, key):
    try:
      return dict.__getitem__(self, self._positions[key])
    except TypeError, e:
      return dict.__getitem__(self, key)
  def __setitem__(self, key, value):
    try:
      self._positions[value.position] = key
    except IndexError, e:
      raise IndexError, "Index out of bounds: this FormattedFile is of size %s, requested line %s" % \
        (self.maxsize, value.position)
    dict.__setitem__(self, key, value)
  def __iter__(self):
    return iter(self.tolist())

  def addline(self, line):
    if not isinstance(line, FormattedLine):
      raise FormatError, "FormattedFiles can only contain FormattedLines, got %s" % type(line)
    self.__setitem__(line.index, line)

  def getindex(self, hash):
    """Get the index value associated with hash.  If hash doesn't exist in FormattedFile,
    returns None"""
    if self.has_key(hash):
      return self[hash].position
    else:
      return None

  def __str__(self):
    return ''.join([ i.string + '\n' for i in self ])

  def tolist(self):
    retlist = []
    for item in self._positions:
      retlist.append(self[item])
    return retlist

  def read(self, file):
    """Return a dictionary of variables as computed by reading in a file and attempting
    to match it to the FormattedLines it contains."""
    return self.__read(pps.path(file).read_lines())

  def lread(self, list):
    "'list read'"
    return self.__read(list)

  def floread(self, flo):
    "'file-like object read'"
    return self.__read([ line.rstrip('\n') for line in flo.readlines() ])

  def __read(self, source):
    if len(source) != len(self):
      raise FormatError, "Size mismatch between FormattedFile (%s lines) and '%s' (%s lines)" % \
        (len(self), file, len(source))

    d = {}

    for v in self:
      # kind of a hack - replace format strings with a re, then escape the
      # string, then un-escape the replacement
      fmtstring_re = re.escape(FMT_FIND.sub('(.+)', v.string)).replace('\(\.\+\)', '(.+)')
      scan = re.compile(fmtstring_re)
      matches = scan.match(source[v.position])
      if matches: groups = matches.groups()
      else:       groups = () # empty tuple

      fmtvars = FMT_FIND.findall(v.string)
      if len(groups) != len(fmtvars):
        raise FormatError("Invalid file format: line %s doesn't match the expected format string '%s': %s" % (v.position, v.string, source))

      for i in range(0, len(fmtvars)):
        d[fmtvars[i]] = groups[i]

    return d

  def write(self, file, **kwargs):
    "Write the formatted file out to a file, using the values in dict as replacement vars"
    pps.path(file).write_lines(self.printf(**kwargs))

  def printf(self, **kwargs):
    content = []
    for line in self:
      try:
        content.append(line.string % kwargs)
      except KeyError, e:
        raise FormatError("Variable '%s' not defined in supplied scope" % e.args[0])

    return content

class FormattedLine:
  "A formatted line structure"

  def __init__(self, string, pos, index, description=None):
    self.position    = pos    # position line is in the file
    self.string      = string # string representing this line, can contain printf-style formatting
    self.index       = index  # index (hash) in FormattedFile to use for this line
    self.description = description # description of what this line is

  def __str__(self): return self.string


#-------- FACTORY FUNCTIONS ---------#

def DictToFormattedFile(dict):
  """Generate a FormattedFile from a dictionary.

  Dictionary should appear as follows:
  <dict name> = {
    <index name> = {
      'string': <string>
      'index': <line number> # optional
    },
    ...
  }"""
  ffile = FormattedFile(len(dict))
  i = 0
  for k,v in dict.items():
    if not v.has_key('string'): raise ValueError, "Malformed dictionary"
    index = v.get('index')
    if index is None: index = i
    ffile.addline(FormattedLine(v.get('string'),
                                int(index),
                                k))
    i += 1
  return ffile

def XmlToFormattedFile(elem):
  """Convert an xmltree element containing one or more <line> nodes in the following format

  <line id="..." index="...">
    <string>...</string>
  </line>

  into a FormattedFile consisting of each line, similar to the way DictToFormattedFile works.
  """
  ffile = FormattedFile(len(elem.xpath('line')))
  i = 0
  for line in elem.xpath('line'):
    index = int(line.attrib.get('index'))
    if index is None: index = i
    ffile.addline(FormattedLine(line.get('string/text()'),
                                index,
                                line.attrib['id']))
    i += 1
  return ffile

#--------- ERRORS ---------#

class FormatError(StandardError):
  """Class of exceptions raised when there is a formatting problem with a
  FormattedFile or FormattedLine"""
