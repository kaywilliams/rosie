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
"""
difftest.py

A flexible, modular status monitoring system for determining whether or
not a given set of data has changed or not.  Allows the client
application to define one or more 'handler' objects that examine some
aspect of the system, program state, or any other variable or condition
to determine whether or not to execute some other function.

For example, say a certain program wishes to track two input files as
well as its own output file.  It might define input and output handlers
that check the file size and modified times; if these both match, then
the handler considers them unchanged. Then, the program can tell by
running status's Status.changed() function whether or not it needs to
regenerate its own output.

Handlers must implement the following interface:
  mdread(metadata): accepts a xmltree.XmlElement instance; responsible
    for setting up internal variables representing whatever was written
    out the last time mdwrite() was called.  If the handler doesn't need
    to read in metadata, this method can pass safely
  mdwrite(root): accepts a xmltree.XmlElement instance; responsible for
    encoding internal variables into xmltree.XmlElements that will be
    written to the mdfile.  If the handler doesn't need to write out
    metadata, this method can pass safely.
  diff(): responsible for computing whether or not a change has taken
    place between the initial execution and the current one.  Returning
    an object with len >= 1 will signify that a change has taken place,
    while returning a len 0 object means that no change has occurred.
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '1.0'
__date__    = 'June 12th, 2007'

from xml.sax import SAXParseException

from systemstudio.util import rxml

def expand(list):
  "Expands a list of lists into a list, in place."
  old = []
  new = []
  # expand all lists in the list
  for item in list:
    if hasattr(item, '__iter__'):
      new.extend(item)
      old.append(item)
  for x in old: list.remove(x)
  for x in new: list.append(x)
  return list

class DiffTest:
  """
  The main status manager class.  Contains a list of handlers, which are classes
  that actually perform the necessary checks.  Also capable of reading and writing
  a metadata file, stored in xml format, which can store information between sessions.
  """
  def __init__(self, mdfile):
    "mdfile is the location to use as the metadata file for storage between executions"
    self.mdfile = mdfile # the location of the file to store information
    self.handlers = [] # a list of registered handlers
    self.debug = False # enable to see very verbose printout of diffs
    self.metadata = None

  def dprint(self, msg):
    if self.debug: print msg

  def addHandler(self, handler):
    "Add a handler that implements the status interface (described above)"
    handler.debug  = self.debug
    handler.dprint = self.dprint
    self.handlers.append(handler)

  def clean_metadata(self):
    for handler in self.handlers:
      handler.clear()
    self.mdfile.rm(force=True)

  def read_metadata(self, handlers=[]):
    """
    Read the file stored at self.mdfile and pass it to each of the
    handler's mdread() functions.
    """
    if self.metadata is None:
      try:
        self.metadata = rxml.config.read(self.mdfile)
      except (ValueError, IOError, SAXParseException, rxml.errors.XmlSyntaxError), e:
        self.metadata = DummyMetadata(self.mdfile)

    if isinstance(self.metadata, rxml.config.ConfigElement):
      handlers = handlers or self.handlers
      if not hasattr(handlers, '__iter__'):
        handlers = [handlers]

      for handler in handlers:
        handler.mdread(self.metadata)

  def write_metadata(self):
    """
    Create an XmlTreeElement from self.mdfile, if it exists, or make a
    new one and pass it to each of the handler's mdwrite() functions.
    Due to the way rxml.config.XmlTreeElements work, mdwrite() doesn't
    need to return any values; xmltree appends are destructive.
    """
    root = rxml.config.Element('metadata')
    for handler in self.handlers:
      handler.mdwrite(root)
    self.mdfile.dirname.mkdirs()
    root.write(self.mdfile)
    self.mdfile.chmod(0644)

  def changed(self, debug=None):
    "Returns true if any handler returns a diff with length greater than 0"
    old_dbgval = self.debug
    if debug is not None: self.debug = debug
    changed = False
    for handler in self.handlers:
      d = handler.diff()
      if len(d) > 0:
        changed = True
    self.debug = old_dbgval
    return changed

  def test(self, debug=None):
    "Perform a full check, from reading metadata to writing"
    self.read_metadata()
    change = self.changed(debug=debug)
    self.write_metadata()
    return change

class DummyMetadata:
  "Represents a metadata file object that doesn't exist."
  def __init__(self, f):
    self.path = f
  def __repr__(self):
    return "DummyMetadata(%s)" % self.path

class NewEntry:
  "Represents an item requested in a handler's data section that is not currently"
  "present in its metadata"
  def __repr__(self):
    return "NewEntry()"
  def __iter__(self):
    return iter([])
  def __len__(self):
    return 0

class NoneEntry:
  "Represents an item requested in a handler's data section that does not exist"
  "for any reason"
  def __init__(self, index):
    "index is the path in the configuration object to this element"
    self.index = index
  def __eq__(self, other):
    try: return self.index == other.index
    except AttributeError: return False
  def __ne__(self, other):
    return not self == other
  def __str__(self):
    return self.__repr__()
  def __repr__(self):
    return "NoneEntry(%s)" % self.index
  def __iter__(self):
    return iter([])
  def __len__(self):
    return 0

from systemstudio.util.difftest.handlers import * # at the end to avoid circular imports
