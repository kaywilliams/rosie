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
__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '1.0'
__date__    = 'June 12th, 2007'

import errno

from rendition import pps
from rendition import rxml

from rendition.difftest           import expand
from rendition.difftest.filesdiff import diff, DiffTuple
from rendition.difftest.handlers  import DiffHandler

class OutputHandler(DiffHandler):
  def __init__(self, data):
    self.name = 'output'
    self.odata = data
    self.oldoutput = {}

    self.tupcls = DiffTuple

    DiffHandler.__init__(self)

    expand(self.odata)

  def clear(self):
    self.oldoutput.clear()

  def mdread(self, metadata):
    for f in metadata.xpath('/metadata/output/file', []):
      self.oldoutput[pps.path(f.get('@path'))] = self.tupcls().fromxml(f)

  def mdwrite(self, root):
    parent = rxml.config.uElement('output', parent=root)
    # write to metadata file
    paths = []
    for file in [ pps.path(x) for x in self.odata ]:
      if not file.exists():
        raise pps.Path.PathError(errno.ENOENT, file)
      paths.extend(file.findpaths(type=pps.constants.TYPE_NOT_DIR))
    for file in paths:
      file = file.normpath()
      parent.append(self.tupcls(file).toxml())

  def diff(self):
    newitems = {}
    for item in self.oldoutput.keys():
      newitems[item] = DiffTuple(item)

    self.diffdict = diff(self.oldoutput, newitems)
    if self.diffdict: self.dprint('output: %s' % self.diffdict)
    return self.diffdict
