from dims import xmltree

from dimsbuild.event import Event
from dimsbuild.main  import apply_flowcontrol

API_VERSION = 5.0

#------ EVENTS ------#
class CleanEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'clean',
      comes_after = ['init'],
    )
    
    self.mdfile = self.get_mdfile()
    self.DATA = {'events': {}}
    self.eventinfo = {}
    
    self.DISTRO_DIR = self.CACHE_DIR / self.pva # remap distro dir #!
  
  def _setup(self):
    for event in self:
      self.eventinfo[event.id] = event.id
      self.DATA['events'].update({event.id: str(event.event_version)})
    
    self.setup_diff(self.mdfile, self.DATA)
    self._add_handler(EventHandler(self.DATA['events']))
  
  def _clean(self):
    self._clean_all()
  
  def _check(self):
    return self.test_diffs()
  
  def _run(self):
    self.log(0, "processing clean")
    self.log(1, "forcing events") 
    # if clean hook version changes, force all
    if self._diff_handlers['events'].diffdict.has_key(self.id):
      prevver, currver = self._diff_handlers['events'].diffdict[self.id]
      if prevver and currver:
        self._clean_all()
    else:
      for hook in self._diff_handlers['events'].diffdict.keys():
        prevver, currver = self._diff_handlers['events'].diffdict[hook]
        if prevver and currver:
          self._force_clean(self.eventinfo[hook])
    
    self.write_metadata()
  
  def _clean_all(self):
    self.log(0, "cleaning all")
    
    self.log(1, "cleaning folders")    
    #! TODO - these should be callbacked
    if self.DISTRO_DIR.exists():
      self.log(2, "cleaning '%s'" % self.DISTRO_DIR)
      self.DISTRO_DIR.rm(recursive=True)
    ##if self.TEMP_DIR.exists():
    ##  self.log(2, "cleaning '%s'" % self.TEMP_DIR)
    ##  self.TEMP_DIR.rm(recursive=True)
    
    ##for dir in [self.TEMP_DIR, self.SOFTWARE_STORE, self.METADATA_DIR]:
    ##  if not dir.exists():
    ##    self.log(2, "creating directory '%s'" % dir)
    ##    dir.mkdirs()
    ##self.mdfile.dirname.mkdirs()
    
  def _force_clean(self, eventid):
    self.log(2, "forcing --clean on %s" % eventid)
    #! the following is currently illegal
    apply_flowcontrol(self.get(eventid), True)

EVENTS = {'ALL': [CleanEvent]}


#------ METADATA HANDLER ------#
class EventHandler:
  def __init__(self, data):
    self.name = 'events'
    
    self.data = data
    self.hooks = {}
    self.diffdict = {}
  
  def clear(self):
    self.hooks.clear()
    self.diffdict.clear()
        
  def mdread(self, metadata):
    for hook in metadata.xpath('/metadata/hooks/hook'):
      self.hooks[hook.get('@id')] = hook.get('version/text()')
  
  def mdwrite(self, root):
    parent = xmltree.uElement('events', parent=root)
    
    for k,v in self.diffdict.items():
      try: parent.remove(parent.get('hook[@id="%s"]' % k))
      except TypeError: pass
      if v[1] is not None:
        e = xmltree.Element('hook', parent=parent, attrs={'id': k})
        xmltree.Element('version', parent=e, text=str(v[1]))
  
  def diff(self):    
    for k,v in self.hooks.items():
      if self.data.has_key(k):
        newv = self.data[k]
        if v != newv:
          self.diffdict[k] = (v, newv)
      else:
        self.diffdict[k] = (v, None)
    
    for k,v in self.data.items():
      if not self.hooks.has_key(k):
        self.diffdict[k] = (None, v)
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict
