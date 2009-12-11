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
libvirt.py

create a libvirt image from the output of virtimage-base
"""

from systembuilder.event import Event

class LibVirtEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'virtimage-libvirt',
      parentid = 'vm',
      requires = ['virtimage-disks', 'virtimage-xml'],
      provides = ['publish-content'],
    )

    self.shouldrun = self.config.getbool('@libvirt', False)

    self.outdir = self.mddir/'images/libvirt'

    self.DATA =  {
      'config': ['@libvirt'],
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    if not self.shouldrun: return

    self.io.add_fpaths(self.cvars['virtimage-disks'], self.outdir)
    self.io.add_fpath(self.cvars['virtimage-xml'], self.outdir)

  def run(self):
    if not self.shouldrun: return

    # this is easy, just copy files
    self.io.sync_input(text="copying image files")

  def apply(self):
    self.io.clean_eventcache()

    if not self.shouldrun: return

    self.cvars.setdefault('publish-content', set()).add(self.outdir)
