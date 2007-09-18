from dims import xmltree

from dimsbuild.event import Event
from dimsbuild.main  import apply_flowcontrol

API_VERSION = 5.0

class AutocleanEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'autoclean',
      comes_after = ['init'],
    )
    
    self.DATA = {'events': {}}
    self.eventinfo = {}
  
  def setup(self):
    for event in self:
      self.eventinfo[event.id] = event.id
      self.DATA['events'].update({event.id: str(event.event_version)})
    
    self.setup_diff(self.DATA)
    self._add_handler(EventHandler(self.DATA['events']))
  
  def run(self):
    self.log(0, "processing autoclean")
    for event in self._diff_handlers['events'].diffdict.keys():
      prevver, currver = self._diff_handlers['events'].diffdict[event]
      if prevver and currver:
        self._force_clean(self.eventinfo[event])
    
    self.write_metadata()
  
  def _force_clean(self, eventid):
    self.log(2, "forcing --clean on %s" % eventid)
    #! the following is currently illegal
    apply_flowcontrol(self.get(eventid), True)

EVENTS = {'ALL': [AutocleanEvent]}


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
    parent = xmltree.uElement('events', parent=root)
    
    for k,v in self.diffdict.items():
      try: parent.remove(parent.get('event[@id="%s"]' % k))
      except TypeError: pass
      if v[1] is not None:
        e = xmltree.Element('event', parent=parent, attrs={'id': k})
        xmltree.Element('version', parent=e, text=str(v[1]))
  
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
