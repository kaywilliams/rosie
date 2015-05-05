#
# Copyright (c) 2015
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
from deploy.event   import Event

from deploy.modules.shared import FileDownloadMixin

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['IsolinuxEvent'],
    description = 'creates an isolinux folder',
    group       = 'installer',
  )

class IsolinuxEvent(Event, FileDownloadMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'isolinux',
      parentid = 'installer',
      ptr = ptr,
      provides = ['isolinux-files', 'boot-config-file', 'os-content'],
      requires = ['anaconda-version', 'base-info', 'installer-repo'],
      conditional = True, # don't run unless provides required by another 
                          # event, i.e. iso or bootiso
    )

    self.DATA = {
      'config':    set(['.']),
      'variables': set(['cvars[\'anaconda-version\']']),
      'input':     set(),
      'output':    set(),
    }

    FileDownloadMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.file_locals = self.locals.L_FILES['isolinux']
    FileDownloadMixin.setup(self)

  def run(self):
    self._download()

  def apply(self):
    self.cvars.setdefault('isolinux-files', {})
    for k,v in self.file_locals.items():
      self.cvars['isolinux-files'][k] = (v['path'], self.OUTPUT_DIR/v['path'])
    self.cvars['boot-config-file'] = \
      self.OUTPUT_DIR/self.file_locals['isolinux.cfg']['path']
