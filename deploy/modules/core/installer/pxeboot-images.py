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
from deploy.util import pps

from deploy.event import Event

from deploy.modules.shared import FileDownloadMixin

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['PxebootImagesEvent'],
    description = 'creates a pxeboot folder',
    group       = 'installer',
  )

class PxebootImagesEvent(Event, FileDownloadMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'pxeboot-images',
      parentid = 'installer',
      ptr = ptr,
      provides = ['pxeboot', 'treeinfo-checksums', 'os-content'],
    )

    self.DATA = {
      'input':  set(),
      'output': set(),
    }

    FileDownloadMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.file_locals = self.locals.L_FILES['pxeboot']
    FileDownloadMixin.setup(self)

  def run(self):
    self._download()

  def apply(self):
    cvar = self.cvars.setdefault('treeinfo-checksums', set())
    for f in self.OUTPUT_DIR.findpaths(type=pps.constants.TYPE_NOT_DIR):
      cvar.add((self.OUTPUT_DIR, f.relpathfrom(self.OUTPUT_DIR)))
