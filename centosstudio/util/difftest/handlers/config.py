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
__author__  = 'Daniel Musgrave <dmusgrave@centosstudio.org>'
__version__ = '1.0'
__date__    = 'June 12th, 2007'

import copy
import difflib

from centosstudio.util import rxml

from centosstudio.util.difftest          import expand, NoneEntry, NewEntry
from centosstudio.util.difftest.handlers import DiffHandler

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

  def mdread(self, metadata):
    for node in metadata.xpath('/metadata/config/value', []):
      path = node.get('@path')
      self.cfg[path] = node.xpath('elements/*', None) or \
                       node.xpath('text/text()', NoneEntry(path))

  def mdwrite(self, root):
    config = rxml.config.Element('config', parent=root)
    for path in self.cdata:
      value = rxml.config.Element('value', parent=config, attrs={'path': path})
      for val in self.config.xpath(path, []):
        if isinstance(val, str): # a string
          rxml.config.Element('text', parent=value, text=val)
        else: # elements
          elements = rxml.config.Element('elements', parent=value)
          elements.append(copy.copy(val)) # append() is destructive

  def diff(self):
    self.diffdict = ConfigDiffDict()
    for path in self.cdata:
      if self.cfg.has_key(path):
        try:
          cfgval = self.config.xpath(path)
        except rxml.errors.XmlPathError:
          cfgval = NoneEntry(path)
        if self.cfg[path] != cfgval:
          self.diffdict[path] = (self.cfg[path], cfgval)
      else:
        try:
          cfgval = self.config.xpath(path)
        except rxml.errors.XmlPathError:
          cfgval = NoneEntry(path)
        self.diffdict[path] = (NewEntry(), cfgval)
    if self.diffdict: self.dprint('config: %s' % self.diffdict)
    return self.diffdict

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
