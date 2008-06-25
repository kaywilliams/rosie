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

from spin.modules.shared import ImageModifyMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['UpdatesImageEvent'],
  description = 'create the updates.img used during anaconda install',
  group       = 'installer',
)

class UpdatesImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'updates-image',
      parentid = 'installer',
      provides = ['updates.img'],
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
    self.image_locals = self.locals.L_FILES['installer']['updates.img']
    ImageModifyMixin.setup(self)

  def run(self):
    self._modify()
