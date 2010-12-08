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
from systemstudio.util import repo
from systemstudio.util import versort

from systemstudio.event import Event, CLASS_META

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['InstallerEvent', 'InstallerSetupEvent'],
  description = 'modules that create core install images',
)

class InstallerEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'installer',
      parentid = 'os',
      properties = CLASS_META,
      provides = ['os-content'],
      suppress_run_message = True,
    )

class InstallerSetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'installer-setup',
      parentid = 'setup',
      provides = ['anaconda-version-supplied'],
      suppress_run_message = True,
    )

    self.DATA = {
      'variables': [],
      'config': ['.'],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.anaconda_version = self.config.get('anaconda-version/text()', None)
    if self.anaconda_version is not None:
      self.anaconda_version = versort.Version(self.anaconda_version)

  def run(self):
    pass

  def apply(self):
    # set cvars
    self.cvars['anaconda-version-supplied'] = self.anaconda_version
