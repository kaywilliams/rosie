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

from spin.modules.shared import FileDownloadMixin

API_VERSION = 5.0
EVENTS = ['Stage2ImagesEvent']

class Stage2ImagesEvent(Event, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'stage2-images',
      parentid = 'installer',
      provides = ['stage2-images'],
      requires = ['anaconda-version', 'base-info', 'installer-repo'],
    )

    self.DATA = {
      'input':  [],
      'output': [],
    }

    FileDownloadMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.file_locals = self.locals.L_FILES['stage2']
    FileDownloadMixin.setup(self)

  def run(self):
    self._download()

  def apply(self):
    # semi hack so that bootiso can contain stage2.img in anaconda >= 11.4.0.40
    self.cvars.setdefault('stage2-images', {})
    for k,v in self.file_locals.items():
      self.cvars['stage2-images'][k] = self.SOFTWARE_STORE/v['path']
