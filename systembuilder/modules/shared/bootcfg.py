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

class BootConfigMixin(object):
  def __init__(self):
    self.bootconfig = BootConfigDummy(self)

class BootConfigDummy(object):
  def __init__(self, ptr):
    self.ptr = ptr
    self.boot_args = None
    self._macros = {}

  def setup(self, defaults=None, include_method=False, include_ks=False):
    self.boot_args = self.ptr.config.get('boot-args/text()', '').split()

    args = defaults or []

    if include_method: self._process_method(args)
    if include_ks:     self._process_ks(args)

    for karg in args:
      self._macros['%%{%s}' % karg.split('=')[0]] = karg

    if self.ptr.config.getbool('boot-args/@use-defaults', 'True'):
      self.boot_args.extend(args)

    if self.ptr.cvars['boot-args']:
      self.boot_args.append(self.cvars['boot-args'].split())

    self.boot_args = [ self._expand_macros(x) for x in self.boot_args ]

  def modify(self, dst, cfgfile=None):

    #FIXME: Also need to remove arguments on on diffs

    boot_args = [ self._expand_macros(x) for x in self.boot_args ]

    config = cfgfile or self.ptr.cvars['boot-config-file']
    lines  = config.read_lines()
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

    dst.rm(force=True)
    dst.write_lines(lines)

  def _expand_macros(self, s):
    for k,v in self._macros.items():
      s = s.replace(k, v)
    return s

  def _process_method(self, args):
    self.ptr.DATA['variables'].append('cvars[\'web-path\']')
    if self.ptr.cvars['web-path'] is not None:
      args.append('%s=%s/os' % (self.ptr.locals.L_BOOTCFG['options']['method'],
                                self.ptr.cvars['web-path']))

  def _process_ks(self, args):
    self.ptr.DATA['variables'].append('cvars[\'ks-path\']')
    if self.ptr.cvars['ks-path'] is not None:
      args.append('%s=file:%s' % (self.ptr.locals.L_BOOTCFG['options']['ks'],
                                  self.ptr.cvars['ks-path']))
