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
from centosstudio.event   import Event

from centosstudio.modules.shared import FileDownloadMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['IsolinuxEvent'],
  description = 'creates an isolinux folder',
  group       = 'installer',
)

class IsolinuxEvent(Event, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'isolinux',
      parentid = 'installer',
      provides = ['isolinux-files', 'boot-config-file', 'os-content'],
      requires = ['anaconda-version', 'base-info', 'installer-repo'],
      conditionally_requires = ['installer-splash'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }

    FileDownloadMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.file_locals = self.locals.L_FILES['isolinux']
    if self.cvars.get('installer-splash', None) is not None:
      ## HACK: adding the 'installer-splash' file with the id
      ## 'FileDownloadMixin' is a pretty big hack. It is done just so
      ## that everything after the setup() method is the same as
      ## before.
      self.io.add_fpath(self.cvars['installer-splash'],
                        self.SOFTWARE_STORE/'isolinux',
                        id='FileDownloadMixin')
      self.file_locals.pop(self.cvars['installer-splash'].basename)
    FileDownloadMixin.setup(self)

  def run(self):
    self._download()

  def apply(self):
    self.cvars.setdefault('isolinux-files', {})
    for k,v in self.file_locals.items():
      self.cvars['isolinux-files'][k] = self.SOFTWARE_STORE/v['path']
    if self.cvars.get('installer-splash', None) is not None:
      splash_image = self.cvars['installer-splash']
      self.cvars['isolinux-files'][splash_image.basename] = splash_image
    self.cvars['boot-config-file'] = \
      self.SOFTWARE_STORE/self.file_locals['isolinux.cfg']['path']
