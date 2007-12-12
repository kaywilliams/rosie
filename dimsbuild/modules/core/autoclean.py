from dims import xmllib

from dimsbuild.event   import Event
from dimsbuild.logging import L1, L2

API_VERSION = 5.0
EVENTS = {'ALL': ['AutocleanEvent']}

class AutocleanEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'autoclean',
      comes_after = ['init'],
      comes_before = ['setup'],
    )

    self.DATA = {'events': {}}
    self.eventinfo = {}

  def setup(self):
    for event in self._getroot():
      self.eventinfo[event.id] = event
      self.DATA['events'].update({event.id: str(event.event_version)})

    self.diff.setup(self.DATA)
    self.diff.add_handler(EventHandler(self.DATA['events']))

    # delete all the folders in the metadata directory that are from events
    # that aren't running this pass
    mdfolders = self.METADATA_DIR.listdir()
    for event in self._getroot():
      try:
        mdfolders.remove(self.METADATA_DIR/event.id)
      except:
        pass

    for mdfolder in mdfolders:
      self.log(4, L2("removing unused event metadata directory '%s'" % mdfolder.basename))
      mdfolder.rm(recursive=True, force=True)

  def run(self):
    for eventid in self.diff.handlers['events'].diffdict.keys():
      prevver, currver = self.diff.handlers['events'].diffdict[eventid]
      if prevver and currver:
        self.log(2, L1("forcing '%s'" % eventid))
        self.eventinfo[eventid].status = True

    self.diff.write_metadata()


#------ METADATA HANDLER ------#
class EventHandler:
  def __init__(self, data):
    self.name = 'events'

    self.data = data
    self.events = {}
    self.diffdict = {}

  def clear(self):
    self.events.clear()
    self.diffdict.clear()

  def mdread(self, metadata):
    for event in metadata.xpath('/metadata/events/event'):
      self.events[event.get('@id')] = event.get('version/text()')

  def mdwrite(self, root):
    parent = xmllib.config.uElement('events', parent=root)

    for k,v in self.data.items():
      e = xmllib.config.Element('event', parent=parent, attrs={'id': k})
      xmllib.config.Element('version', parent=e, text=str(v))

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
