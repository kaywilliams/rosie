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
from rendition import pps

from spin.event   import Event

API_VERSION = 5.0
EVENTS = {'installer': ['KickstartEvent']}

class KickstartEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'kickstart',
      version = 1,
      provides = ['kickstart-file', 'ks-path', 'initrd-image-content'],
    )

    self.DATA = {
      'config': ['.'],
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.add_xpath('.', self.SOFTWARE_STORE, id='kickstart-file')

  def run(self):
    self.io.sync_input(cache=True)

  def apply(self):
    self.cvars['kickstart-file'] = self.io.list_output(what='kickstart-file')[0]
    self.cvars['ks-path'] = pps.path('/%s' % self.cvars['kickstart-file'].basename)

  def verify_cvars(self):
    "cvars are set"
    self.verifier.failUnlessSet('ks-path')
