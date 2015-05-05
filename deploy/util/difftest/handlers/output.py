#
# Copyright (c) 2015
# Deploy Foundation. All rights reserved.
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
__author__  = 'Daniel Musgrave <dmusgrave@deployproject.org>'
__version__ = '1.0'
__date__    = 'June 12th, 2007'

import errno

from deploy.util import pps
from deploy.util import rxml

from deploy.util.difftest           import expand
from deploy.util.difftest.filesdiff import diff, DiffTuple
from deploy.util.difftest.handlers  import DiffHandler

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

  def mdread(self, metadata, mddir, *args, **kwargs):
    for f in metadata.xpath('/metadata/output/file', []):
      abspath = mddir / pps.path(f.getxpath('@path'))
      self.oldoutput[abspath] = self.tupcls().fromxml(f, path=abspath)

  def mdwrite(self, root, mddir, *args, **kwargs):
    parent = rxml.config.uElement('output', parent=root)
    # write to metadata file
    paths = set()
    for file in [ pps.path(x) for x in set(self.odata) ]:
      if not file.exists():
        raise pps.Path.PathError(errno.ENOENT, file)
      for f in file.findpaths(type=pps.constants.TYPE_NOT_DIR):
        paths.add(f)
    for file in paths:
      abspath = file.normpath()
      if abspath.startswith(mddir):
        relpath = abspath[len(mddir + '/'):]
      else: relpath = abspath 
      parent.append(self.tupcls(relpath, abspath).toxml())

  def diff(self):
    newitems = {}
    for item in self.oldoutput.keys():
      newitems[item] = DiffTuple(item)

    self.diffdict = diff(self.oldoutput, newitems)
    if self.diffdict: self.dprint('output: %s' % self.diffdict)
    return self.diffdict
