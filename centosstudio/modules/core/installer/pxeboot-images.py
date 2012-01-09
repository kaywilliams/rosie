#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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
from centosstudio.util import pps

from centosstudio.event import Event

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PxebootImagesEvent'],
  description = 'creates a pxeboot folder',
  group       = 'installer',
)

class PxebootImagesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pxeboot-images',
      parentid = 'installer',
      provides = ['pxeboot', 'treeinfo-checksums', 'os-content'],
      requires = ['isolinux-files'],
    )

    self.DATA = {
      'input':  [],
      'output': [],
    }

    self.pxebootdir = self.SOFTWARE_STORE/'images/pxeboot'

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.add_fpath(self.cvars['isolinux-files']['vmlinuz'],    self.pxebootdir)
    self.io.add_fpath(self.cvars['isolinux-files']['initrd.img'], self.pxebootdir)

  def run(self):
    self.io.process_files(cache=True)

  def apply(self):
    cvar = self.cvars.setdefault('treeinfo-checksums', set())
    for f in self.SOFTWARE_STORE.findpaths(type=pps.constants.TYPE_NOT_DIR):
      cvar.add((self.SOFTWARE_STORE, f.relpathfrom(self.SOFTWARE_STORE)))
