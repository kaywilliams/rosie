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
__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '1.0'
__date__    = 'June 12th, 2007'

import textwrap

from systembuilder.util import rxml

from systembuilder.util.difftest          import expand, NoneEntry, NewEntry
from systembuilder.util.difftest.handlers import DiffHandler

NEW = '-'
NONE = '<not found>'

class VariablesHandler(DiffHandler):
  def __init__(self, data, obj):
    self.name = 'variables'

    self.vdata = data
    self.obj = obj
    self.vars = {}

    DiffHandler.__init__(self)

    expand(self.vdata)

  def clear(self):
    self.vars.clear()

  def mdread(self, metadata):
    for node in metadata.xpath('/metadata/variables/value', []):
      item = node.get('@variable')
      if len(node.getchildren()) == 0:
        self.vars[item] = NoneEntry(item)
      else:
        self.vars[item] = rxml.serialize.unserialize(node[0])

  def mdwrite(self, root):
    vars = rxml.config.Element('variables', parent=root)
    for var in self.vdata:
      parent = rxml.config.Element('value', parent=vars, attrs={'variable': var})
      val = eval('self.obj.%s' % var)
      parent.append(rxml.serialize.serialize(val))

  def diff(self):
    self.diffdict = VariablesDiffDict()
    for var in self.vdata:
      try:
        val = eval('self.obj.%s' % var)
      except AttributeError:
        val = NoneEntry(var)
      if self.vars.has_key(var):
        if self.vars[var] != val:
          self.diffdict[var] = (self.vars[var], val)
      else:
        self.diffdict[var] = (NewEntry(), val)

    for old_var in self.vars:
      if old_var not in self.vdata:
        # A variable is not being tracked anymore.  Definitely a
        # change worth noting.
        self.diffdict[old_var] = (self.vars[old_var], NoneEntry(old_var))
    if self.diffdict: self.dprint('variables: %s' % self.diffdict)
    return self.diffdict


class VariablesDiffDict(dict):
  width = 35 # max width of var returns (should be less than half term width)

  def __str__(self): return self.__repr__()
  def __repr__(self):
    s = ''

    for key, vartup in self.items():
      metadata, memory = vartup

      s += key + '\n'
      s += '  %-35.35s  %-35.35s\n' % ('Metadata', 'Memory')

      if metadata:
        if isinstance(metadata, NewEntry):
          c1 = NEW
        else:
          c1 = repr(metadata)
      else:
        c1 = NONE

      if memory:
        if isinstance(memory, NewEntry):
          c2 = NEW
        else:
          c2 = repr(memory)
      else:
        c2 = NONE

      s += '\n'.join(_wrap_lines(c1, c2, self.width)) + '\n'

    return s

def _wrap_lines(s1, s2, width):
  l1 = textwrap.wrap(s1, width-1)
  l2 = textwrap.wrap(s2, width-1)

  if len(l1) > len(l2):
    for i in range(len(l2), len(l1)):
      l2.append(' '*width)
  elif len(l1) < len(l2):
    for i in range(len(l1), len(l2)):
      l1.append(' '*width)

  lf = []
  for i in range(0, len(l1)):
    lf.append('  %-35.35s  %-35.35s' % (l1[i], l2[i]))
  return lf
