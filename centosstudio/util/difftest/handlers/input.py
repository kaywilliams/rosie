#
# Copyright (c) 2011
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
__author__  = 'Daniel Musgrave <dmusgrave@centosstudio.org>'
__version__ = '1.0'
__date__    = 'June 12th, 2007'

from centosstudio.util import pps
from centosstudio.util import rxml

from centosstudio.util.difftest           import expand, DummyMetadata
from centosstudio.util.difftest.filesdiff import diff, DiffTuple
from centosstudio.util.difftest.handlers  import DiffHandler

class InputHandler(DiffHandler):
  def __init__(self, data):
    self.name = 'input'
    self.idata = data
    self.oldinput = {} # {file: stats}
    self.newinput = {} # {file: stats}

    self.tupcls = DiffTuple # the factory function to use to create diff tuples

    DiffHandler.__init__(self)

    expand(self.idata)

  def clear(self):
    self.oldinput.clear()

  def mdread(self, metadata):
    for f in metadata.xpath('/metadata/input/file', []):
      self.oldinput[pps.path(f.get('@path'))] = self.tupcls().fromxml(f)

  def mdwrite(self, root):
    parent = rxml.config.Element('input', parent=root)
    for datum in self.idata:
      for ifile in pps.path(datum).findpaths(type=pps.constants.TYPE_NOT_DIR):
        parent.append((self.newinput.get(ifile) or
                       self.tupcls(ifile)).toxml())

  def diff(self):
    self.newinput = {}
    for datum in self.idata:
      ifiles = pps.path(datum).findpaths(type=pps.constants.TYPE_NOT_DIR)
      if not ifiles: raise ValueError('No file(s) found at %s' % datum)
      for ifile in ifiles:
        self.newinput[ifile] = self.tupcls(ifile)
    self.diffdict = diff(self.oldinput, self.newinput)
    if self.diffdict: self.dprint('input: %s' % self.diffdict)
    return self.diffdict
