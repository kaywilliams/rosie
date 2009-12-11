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
"""
vmware.py

create a vmware image from the output of virtimage-base
"""

import virtconv.formats

from rendition import pps

from systembuilder.event   import Event
from systembuilder.logging import L1, L2

class VmwareEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'virtimage-vmware',
      parentid = 'vm',
      requires = ['virtimage-disks', 'virtimage-xml'],
      provides = ['publish-content'],
    )

    self.shouldrun = self.config.getbool('@vmware', False)

    self.outdir = self.mddir/'images/vmware'

    self.DATA =  {
      'config': ['@vmware'],
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    if not self.shouldrun: return

    # set up parsers
    self.in_parser  = virtconv.formats.parser_by_name('virt-image')
    self.out_parser = virtconv.formats.parser_by_name('vmx')

    # a few variables for easier use of virtconv, in run
    self.disk_dir = self.cvars['virtimage-disks'][0].dirname
    self.conf     = ( self.outdir/self.cvars['virtimage-xml']
                        .basename
                        .splitext()[0]+self.out_parser.suffix )
    self.diskname = self.outdir/'%s.vmdk'

    # add inputs and outputs
    for disk in self.cvars['virtimage-disks']:
      self.DATA['input'].append(disk)
      self.DATA['output'].append(self.diskname % disk.basename.splitext()[0])
    self.DATA['input'].append(self.cvars['virtimage-xml'])
    self.DATA['output'].append(self.conf)

  def run(self):
    if not self.shouldrun: return

    vmdef = self.in_parser.import_file(self.cvars['virtimage-xml'])
    # convert disks
    self.log(3, L1("converting disks"))
    for d in vmdef.disks.values():
      self.log(4, L2(pps.path(d.path).basename))
      d.convert(self.disk_dir, self.outdir, 'vmdk')
    # write config
    self.log(3, L1("writing conf"))
    self.out_parser.export_file(vmdef, self.conf)

  def apply(self):
    self.io.clean_eventcache()

    if not self.shouldrun: return

    self.cvars.setdefault('publish-content', set()).add(self.outdir)
