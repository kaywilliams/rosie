from dims import xmltree

from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.interface import EventInterface

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'clean',
    'properties': EVENT_TYPE_MDLR|EVENT_TYPE_PROC,
    'conditional-requires': ['applyopt'],
    'parent': 'ALL',
    'interface': 'CleanInterface',
  },
]

HOOK_MAPPING = {
  'CleanHook': 'clean',
}

#------ METADATA HANDLERS ------#
class HookHandler:
  def __init__(self, data):
    self.name = 'hooks'
    
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
    parent = xmltree.uElement('hooks', parent=root)

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

#------ INTERFACES ------#
class CleanInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self.dispatch = self._base.dispatch

#------ HOOKS ------#
class CleanHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'clean.clean'

    self.DATA = {'hooks': {}}
    self.hookInfo = {}

    self.interface = interface
    self.dispatch = self.interface.dispatch

  def setup(self):
    for event in self.dispatch.event:
      for hook in event.hooks:
        self.hookInfo[hook.ID] = event.id
        self.DATA['hooks'].update({hook.ID: str(hook.VERSION)})
        
    self.interface.setup_diff(self.interface.METADATA_DIR/'clean.md', self.DATA)
    self.interface.add_handler(HookHandler(self.DATA['hooks']))
  
  def clean(self):
    self._clean_all()
    
  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "processing clean")
    self.interface.log(1, "forcing events") 
    # if clean hook version changes, force all
    if self.interface.handlers['hooks'].diffdict.has_key(self.ID):      
      prevver, currver = self.interface.handlers['hooks'].diffdict[self.ID]
      if prevver and currver:
        self._clean_all()
    else:
      for hook in self.interface.handlers['hooks'].diffdict.keys():
        prevver, currver = self.interface.handlers['hooks'].diffdict[hook]
        if prevver and currver:
          self._force_clean(self.hookInfo[hook])
  
    self.interface.write_metadata()
  
  def _clean_all(self):
    self.interface.log(0, "cleaning all")
    
    self.interface.log(1, "cleaning folders")    
    #! TODO - these should be callbacked
    if self.interface.DISTRO_DIR.exists():
      self.interface.log(2, "cleaning '%s'" % self.interface.DISTRO_DIR)
      self.interface.DISTRO_DIR.rm(recursive=True)
    if self.interface.TEMP_DIR.exists():
      self.interface.log(2, "cleaning '%s'" % self.interface.TEMP_DIR)
      self.interface.TEMP_DIR.rm(recursive=True)
      
    #! the following is currently illegal
    for dir in [self.interface.TEMP_DIR, self.interface.SOFTWARE_STORE,
                self.interface.METADATA_DIR]:
      if not dir.exists():
        self.interface.log(2, "creating directory '%s'" % dir)
        dir.mkdirs()
    
    
  def _force_clean(self, eventid):
    self.interface.log(2, "forcing --clean on %s" % eventid)
    #! the following is currently illegal
    self.interface._base._apply_flowcontrol(self.interface._base.dispatch.get(eventid), True)
