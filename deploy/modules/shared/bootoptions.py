#
# Copyright (c) 2013
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

class BootOptionsMixin(object):
  def __init__(self, *args, **kwargs):
    self.conditionally_requires.update(['publish-setup-options', 
                                        'publish-ksfile', 'publish-ksname'])
    self.bootoptions = BootOptionsDummy(self)
    self.DATA['variables'].append('bootoptions.boot_args')

    self.boot_options_mixin_version = '1.01'
    self.DATA['variables'].append('boot_options_mixin_version')

class BootOptionsDummy(object):
  def __init__(self, ptr):
    self.ptr = ptr
    self.boot_args = None

  def setup(self, defaults=None, include_method=False, include_ks=False):
    self.boot_args = \
      self.ptr.cvars['publish-setup-options']['boot-options'].split()
    self.ptr.webpath = self.ptr.cvars['publish-setup-options']['webpath']

    args = defaults or []

    if include_method: self._process_method(args)
    if include_ks:     self._process_ks(include_ks, args)

    self.boot_args.extend(args)

  def modify(self, dst, cfgfile=None):

    #FIXME: Also need to remove arguments on on diffs

    config = cfgfile or self.ptr.cvars['boot-config-file']
    lines  = config.read_lines()
    _label = False # have we seen a label line yet?

    for i in range(0, len(lines)):
      tokens = lines[i].strip().split()
      if not tokens: continue
      if tokens[0] == 'menu' and tokens[1] == 'title':
        lines[i] = 'menu title Welcome to %s!' % self.ptr.fullname
      if not self.boot_args: continue
      if   tokens[0] == 'label': _label = True
      elif tokens[0] == 'append':
        if   not _label: continue
        elif len(tokens) < 2: continue
        elif tokens[1] == '-': continue
        lines[i] = '%s %s' % (lines[i].rstrip(), ' '.join(self.boot_args))

    dst.rm(force=True)
    dst.write_lines(lines)

  def _process_method(self, args):
    self.ptr.DATA['variables'].append('webpath')
    if self.ptr.webpath is not None:
      args.append('%s=%s' % (self.ptr.locals.L_BOOTCFG['options']['method'],
                                self.ptr.webpath))

  def _process_ks(self, include_ks, args):
    self.ptr.DATA['variables'].append('cvars[\'publish-ksname\']')
    ksname = self.ptr.cvars['publish-ksname']
    if self.ptr.cvars['publish-ksfile']:
      if include_ks == 'local':
        args.append('%s=file:/%s' % (self.ptr.locals.L_BOOTCFG['options']['ks'],
                                     ksname))
      if include_ks == 'web':
        self.ptr.DATA['variables'].append('webpath')
        args.append('%s=%s/%s' % (self.ptr.locals.L_BOOTCFG['options']['ks'],
                                  self.ptr.webpath, ksname))
