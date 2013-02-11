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

from deploy.util.pps.constants import TYPE_NOT_DIR

from deploy.event   import Event
from deploy.dlogging import L1

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['FilesEvent'],
    description = 'adds arbitrary files and folders to the repository tree',
  )

class FilesEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'files',
      parentid = 'os-events',
      ptr = ptr,
      provides = ['os-content',],
    )

    self.DATA =  {
      'variables': [],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.add_xpath('files', self.REPO_STORE)

  def run(self):
    self.io.process_files()
