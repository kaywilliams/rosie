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

import re

class BootOptionsMixin(object):
  def __init__(self, *args, **kwargs):
    self.conditionally_requires.update(['publish-setup-options', 
                                        'publish-ksfile', 'publish-ksname'])
    self.bootoptions = BootOptionsDummy(self)

    self.boot_options_mixin_version = '1.01'
    self.DATA['variables'].append('boot_options_mixin_version')

class BootOptionsDummy(object):
  def __init__(self, ptr):
    self.ptr = ptr
    self.boot_args = None

  def setup(self, defaults=None, include_method=False, include_ks=False):
    # mkisofs limits the disc label to 32 characters
    self.disc_label = ('%s %s %s' % (self.ptr.fullname, 
                                    self.ptr.version, 
                                    self.ptr.arch))[:32]

    self.boot_args = \
      self.ptr.cvars['publish-setup-options']['boot-options'].split()
    self.ptr.webpath = self.ptr.cvars['publish-setup-options']['webpath']

    args = defaults or []

    if include_method: self._process_method(include_method, args)
    if include_ks:     self._process_ks(include_ks, args)

    self.boot_args.extend(args)

    self.ptr.DATA['variables'].extend(['bootoptions.boot_args',
                                       'bootoptions.disc_label'])

  def modify(self, dst, cfgfile=None):
    #FIXME: Also need to remove arguments on diffs

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
        # todo: expose this in locals
        lines[i] = re.sub('inst.stage2[^\s]+', 
               r'inst.stage2=hd:LABEL=%s' % 
               self.disc_label.replace(' ', r'\x20'),
               lines[i])
        lines[i] = '%s %s' % (lines[i].rstrip(), ' '.join(self.boot_args))

    dst.rm(force=True)
    lines = [ x.encode('utf8') for x in lines ]
    dst.write_lines(lines)

  def _process_method(self, include_method, args):
    if include_method == 'cdrom':
      if self.ptr.locals.L_BOOTCFG['options']['cdrom-requires-method']:
        args.append('%s=cdrom' % 
                    self.ptr.locals.L_BOOTCFG['options']['method'])
    if include_method == 'web':
      self.ptr.DATA['variables'].append('webpath')
      if self.ptr.webpath is not None:
        args.append('%s=%s' % (self.ptr.locals.L_BOOTCFG['options']['method'],
                                  self.ptr.webpath))

  def _process_ks(self, include_ks, args):
    self.ptr.DATA['variables'].append('cvars[\'publish-ksname\']')
    ksname = self.ptr.cvars['publish-ksname']
    if self.ptr.cvars['publish-ksfile']:
      if include_ks == 'cdrom':
        args.append('%s=%s/%s' % (
                    self.ptr.locals.L_BOOTCFG['options']['ks'],
                    self.ptr.locals.L_BOOTCFG['options']['ks-cdrom-path'],
                    ksname))
      if include_ks == 'web':
        self.ptr.DATA['variables'].append('webpath')
        args.append('%s=%s/%s' % (self.ptr.locals.L_BOOTCFG['options']['ks'],
                                  self.ptr.webpath, ksname))
