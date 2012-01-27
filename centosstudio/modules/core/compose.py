#
# Copyright (c) 2012
# CentOS Solutions Foundation. All rights reserved.
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

from centosstudio.util.pps.constants import TYPE_NOT_DIR

from centosstudio.event   import Event
from centosstudio.cslogging import L1

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ComposeEvent'],
  description = 'creates an os folder',
)

class ComposeEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'compose',
      parentid = 'os-events',
      provides = ['os-dir', 'publish-content',],
      requires = ['os-content'],
    )

    self.DATA =  {
      'variables': [],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.events = []
    for event in self._getroot():
      if 'os-content' in event.provides:
        event_output_dir = self.METADATA_DIR/event.id/'output/os'
        if event_output_dir.exists():
          self.events.append(event.id)
          self.io.add_fpaths(event_output_dir.listdir(all=True),
                             self.SOFTWARE_STORE, id=event.id)

  def run(self):
    # create composed tree
    self.log(1, L1("linking files"))
    for event in self.events:
      self.io.process_files(link=True, what=event, text=None)

  def apply(self):
    self.cvars['os-dir'] = self.SOFTWARE_STORE
    self.cvars.setdefault('publish-content', set()).add(self.SOFTWARE_STORE)

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnlessSet('os-dir')
