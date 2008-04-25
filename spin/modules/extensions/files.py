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
"""
files.py

Includes user-provided files and folders within the distribution folder.
"""

from spin.event   import Event

API_VERSION = 5.0
EVENTS = {'os': ['FilesEvent']}

class FilesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'files',
      provides = ['os-contents'],
    )

    self.DATA =  {
      'config': ['.'],
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.add_xpath('path', self.SOFTWARE_STORE)

  def run(self):
    self.io.sync_input(cache=True)

  def apply(self):
    self.io.clean_eventcache()

  def error(self, e):
    # performing a subset of Event.error since sync handles partially downloaded files
    if self.mdfile.exists():
      debugdir=(self.mddir + '.debug')
      debugdir.mkdir()
      self.mdfile.rename(debugdir / self.mdfile.basename)
