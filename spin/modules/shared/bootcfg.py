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
from rendition import pps

from rendition.xmllib.config import Macro

from spin.constants import BOOLEANS_TRUE

P = pps.Path

class BootConfigMixin(object):
  def __init__(self):
    self.bootconfig = BootConfigDummy(self)

class BootConfigDummy(object):
  def __init__(self, ptr):
    self.ptr = ptr
    self.boot_args = None
    self._macros = {}

  def setup(self, defaults=None):
    self.boot_args = self.ptr.config.get('boot-config/append-args/text()', '').split()
    if defaults:
      for karg in defaults:
        self._macros['%%{%s}' % karg.split('=')[0]] = karg
      if self.ptr.config.get('boot-config/@use-defaults', 'True') in BOOLEANS_TRUE:
        self.boot_args.extend(defaults)
    if self.ptr.cvars['boot-args']:
      self.boot_args.append(self.cvars['boot-args'].split())

    self.boot_args = [ self._expand_macros(x) for x in self.boot_args ]

  def modify(self, dst, cfgfile=None):

    boot_args = [ self._expand_macros(x) for x in self.boot_args ]

    config = P(self.ptr.config.get('boot-config/file/text()',
               cfgfile or self.ptr.cvars['boot-config-file']))
    lines = config.read_lines()
    _label = False # have we seen a label line yet?

    for i in range(0, len(lines)):
      tokens = lines[i].strip().split()
      if not tokens: continue
      if tokens[0] == 'menu' and tokens[1] == 'title':
        lines[i] = 'menu title Welcome to %s!' % self.ptr.fullname
      if not boot_args: continue
      if   tokens[0] == 'label': _label = True
      elif tokens[0] == 'append':
        if   not _label: continue
        elif len(tokens) < 2: continue
        elif tokens[1] == '-': continue
        lines[i] = '%s %s' % (lines[i].rstrip(), ' '.join(boot_args))

    dst.remove()
    dst.write_lines(lines)

  def _expand_macros(self, s):
    for k,v in self._macros.items():
      s = s.replace(k, v)
    return s

  def _process_method(self, args):
    if self.ptr.cvars['web-path']:
      args.append('method=%s/os' % self.ptr.cvars['web-path'])

  def _process_ks(self, args):
    if self.ptr.cvars['ks-path']:
      args.append('ks=file:%s' % self.ptr.cvars['ks-path'])
