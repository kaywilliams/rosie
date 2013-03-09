#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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
from deploy.util import rxml

from deploy.util.difftest.handlers import DiffHandler

from deploy.event   import Event
from deploy.dlogging import L1, L2

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['AutocleanEvent'],
    description = 'cleans the cache when modules are disabled or updated',
  )

class AutocleanEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'autoclean',
      parentid = 'all',
      ptr = ptr,
      comes_after  = ['init'],
      conditionally_comes_before = ['setup-events'],
    )

    self.DATA = {'events': {}}

  def setup(self):
    for event in self._getroot():
      if event.enabled:
        self.DATA['events'].update({event.id: str(event.event_version)})

    self.diff.setup(self.DATA)
    self.diff.add_handler(EventHandler(self.DATA['events']))

    # delete all the folders in the metadata directory that are from events
    # that aren't running this pass
    # TODO - move this into run method
    mdfolders = self.METADATA_DIR.listdir()
    for event in self._getroot():
      if event.enabled:
        try:
          mdfolders.remove(self.METADATA_DIR/event.id)
        except:
          pass

    for mdfolder in mdfolders:
      self.log(4, L2("removing unused event metadata directory '%s'" % mdfolder.basename))
      mdfolder.rm(recursive=True, force=True)

  def run(self):
    for eventid, difftup in self.diff.events.difference().items():
      prevver, currver = difftup
      if prevver and currver:
        self.log(2, L1("forcing '%s'" % eventid))
        self._getroot().get(eventid).status = True


#------ METADATA HANDLER ------#
class EventHandler(DiffHandler):
  def __init__(self, data):
    self.name = 'events'

    self.data = data
    self.events = {}

    DiffHandler.__init__(self)

  def clear(self):
    self.events.clear()
    self.diffdict.clear()

  def mdread(self, metadata, *args, **kwargs):
    for event in metadata.xpath('/metadata/events/event'):
      self.events[event.getxpath('@id')] = event.getxpath('version/text()')

  def mdwrite(self, root, *args, **kwargs):
    parent = rxml.tree.uElement('events', parent=root)

    for k,v in self.data.items():
      e = rxml.tree.Element('event', parent=parent, attrs={'id': k})
      rxml.tree.Element('version', parent=e, text=str(v))

  def diff(self):
    for k,v in self.events.items():
      if self.data.has_key(k):
        newv = self.data[k]
        if v != newv:
          self.diffdict[k] = (v, newv)
      else:
        self.diffdict[k] = (v, None)

    for k,v in self.data.items():
      if not self.events.has_key(k):
        self.diffdict[k] = (None, v)
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict
