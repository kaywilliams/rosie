#
# Copyright (c) 2010
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
from rendition import pps

from systembuilder.event import Event

from systembuilder.modules.shared import ImageModifyMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['UpdatesImageEvent'],
  description = 'creates an updates.img file',
  group       = 'installer',
)

class UpdatesImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'updates-image',
      parentid = 'installer',
      provides = ['updates.img', 'treeinfo-checksums'],
      requires = ['anaconda-version', 'installer-repo'],
      conditionally_requires = ['updates-image-content'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }

    ImageModifyMixin.__init__(self, 'updates.img')

  def error(self, e):
    try:
      self._close()
    except:
      pass
    Event.error(self, e)

  def setup(self):
    # ImageModifyMixin setup
    self.image_locals = self.locals.L_FILES['installer']['updates.img']
    ImageModifyMixin.setup(self)
    self.add_or_create_image()

  def run(self):
    self._modify()

  def apply(self):
    ImageModifyMixin.apply(self)
    cvar = self.cvars.setdefault('treeinfo-checksums', set())
    for file in self.SOFTWARE_STORE.findpaths(type=pps.constants.TYPE_NOT_DIR):
      cvar.add((self.SOFTWARE_STORE, file.relpathfrom(self.SOFTWARE_STORE)))
