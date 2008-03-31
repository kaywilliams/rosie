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
from spin.event   import Event

from spin.modules.shared import FileDownloadMixin, BootConfigMixin

API_VERSION = 5.0
EVENTS = {'installer': ['IsolinuxEvent']}

class IsolinuxEvent(Event, FileDownloadMixin, BootConfigMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'isolinux',
      provides = ['isolinux-files', 'boot-config-file'],
      requires = ['anaconda-version', 'base-info', 'base-repoid'],
      conditionally_requires = ['ks-path', 'boot-args'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }

    FileDownloadMixin.__init__(self)
    BootConfigMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    boot_arg_defaults = []
    self.bootconfig._process_ks(boot_arg_defaults)
    self.bootconfig.setup(defaults=boot_arg_defaults)
    self.file_locals = self.locals.L_FILES['isolinux']
    FileDownloadMixin.setup(self)

  def run(self):
    self._download()
    self.bootconfig.modify(
      self.SOFTWARE_STORE/self.file_locals['isolinux.cfg']['path'],
      self.SOFTWARE_STORE/self.file_locals['isolinux.cfg']['path'])
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()

    self.cvars['isolinux-files'] = {}
    for k,v in self.file_locals.items():
      self.cvars['isolinux-files'][k] = self.SOFTWARE_STORE/v['path']

    self.cvars['boot-config-file'] = \
      self.SOFTWARE_STORE/self.file_locals['isolinux.cfg']['path']
