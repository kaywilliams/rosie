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

import copy
import difflib

from deploy.util           import rxml
from deploy.util.rxml.tree import XML_NS

from deploy.util.difftest          import expand, NoneEntry, NewEntry
from deploy.util.difftest.handlers import DiffHandler

class ConfigHandler(DiffHandler):
  def __init__(self, data, config):
    self.name = 'config'

    self.cdata = data
    self.config = config
    self.cfg = {}

    DiffHandler.__init__(self)

    expand(self.cdata)

  def clear(self):
    self.cfg.clear()

  def mdread(self, metadata, *args, **kwargs):
    for node in metadata.xpath('/metadata/config/value', []):
      path = node.getxpath('@path')
      self.cfg[path] = node.xpath('elements/*', None) or \
                       node.xpath('text/text()', NoneEntry(path))

  def mdwrite(self, root, *args, **kwargs):
    config = rxml.config.Element('config', parent=root)
    for path in set(self.cdata):
      value = rxml.config.Element('value', parent=config, attrib={'path': path})
      for val in self._get_values(path, []):
        if isinstance(val, str): # a string
          rxml.config.Element('text', parent=value, text=val)
        else: # elements
          elements = rxml.config.Element('elements', parent=value)
          elements.append(val)

  def diff(self):
    self.diffdict = ConfigDiffDict()
    for path in set(self.cdata):
      if self.cfg.has_key(path):
        cfgval = self._get_values(path)
        if self.cfg[path] != cfgval:
          self.diffdict[path] = (self.cfg[path], cfgval)
      else:
        cfgval = self._get_values(path)
        self.diffdict[path] = (NewEntry(), cfgval)
    if self.diffdict: self.dprint('config: %s' % self.diffdict)
    return self.diffdict

  def _get_values(self, path, fallback=None):
    if not fallback:
      try:
        values = self.config.xpath(path)
      except rxml.errors.XmlPathError:
        values = NoneEntry(path)
        return values
    else:
      values = self.config.xpath(path, fallback)

    # ignore xml:base for diff testing
    for i, val in enumerate(values):
      if not isinstance(val, basestring):
        val = copy.deepcopy(val)
        for elem in val.iter():
          if '{%s}base' % XML_NS in elem.attrib:
            del elem.attrib['{%s}base' % XML_NS]
        values[i] = val

    return values

class ConfigDiffDict(dict):
  def __str__(self): return self.__repr__()
  def __repr__(self):
    s = ''

    def ndiff(a,b):
      if a is None:
        a = []
      else:
        a = str(a).split('\n')
      if b is None:
        b = []
      else:
        b = str(b).split('\n')
      return '\n'.join(difflib.ndiff(a,b))

    for key, difftup in self.items():
      metadata, memory = difftup
      s += key + '\n'

      if isinstance(metadata, NoneEntry) or isinstance(metadata, NewEntry):
        metadata = []
      if isinstance(memory, NoneEntry) or isinstance(memory, NewEntry):
        memory = []
      s += '\n'.join(map(ndiff, metadata, memory))

    return s
