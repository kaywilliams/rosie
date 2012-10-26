#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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

from repostudio.util.pps.constants import TYPE_NOT_DIR

from repostudio.event   import Event
from repostudio.cslogging import L1

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['ComposeEvent'],
    description = 'creates an os folder',
  )

class ComposeEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'compose',
      parentid = 'os-events',
      ptr = ptr,
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
        # calculate event_output_dir relative to compose output dir
        suffix = self.REPO_STORE[len(self.METADATA_DIR):].replace(
                 self.id, event.id)
        event_output_dir = self.METADATA_DIR // suffix
        if event_output_dir.exists():
          self.events.append(event.id)
          self.io.add_fpaths(event_output_dir.listdir(all=True),
                             self.REPO_STORE, id=event.id)

  def run(self):
    # create composed tree
    self.log(1, L1("linking files"))
    for event in self.events:
      self.io.process_files(link=True, what=event, text=None)

  def apply(self):
    self.cvars['os-dir'] = self.REPO_STORE

    self.cvars.setdefault('publish-content', set())
    for p in self.cvars['os-dir'].findpaths(mindepth=1, maxdepth=1):
      self.cvars['publish-content'].add(p)

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnlessSet('os-dir')
