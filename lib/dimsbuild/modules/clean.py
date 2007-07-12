from os.path import exists, join

from dims import osutils
from dims import xmltree

from dimsbuild import event

from dimsbuild.interface import DiffMixin, EventInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'clean',
    'properties': event.EVENT_TYPE_MDLR|event.EVENT_TYPE_PROC,
    'conditional-requires': ['applyopt'],
    'parent': 'ALL',
    'interface': 'CleanInterface',
  },
]

HOOK_MAPPING = {
  'CleanHook': 'clean',
}

#--------- METADATA HANDLERS ----------#
class HookHandler:
  def __init__(self, data):
    self.data = data
    self.hooks = {}
    self.diffdict = {}

  def clean(self):
    self.hooks.clear()
    self.diffdict.clear()
    
  def mdread(self, metadata):
    for hook in metadata.xpath('/metadata/hooks/hook'):
      self.hooks[hook.get('@id')] = hook.get('version/text()')

  def mdwrite(self, root):
    try: root.remove(root.get('hooks'))
    except TypeError: pass
    
    parent = xmltree.Element('hooks', parent=root)
    for k,v in self.data.items():
      e = xmltree.Element('hook', parent=parent, attrs={'id': k})
      xmltree.Element('version', parent=e, text=str(v))

  def diff(self):
    diff = {}
    for k,v in self.hooks.items():
      if self.data.has_key(k):
        newv = self.data[k]
        if v != newv:
          diff[k] = (v, newv)
    self.diffdict.update(diff)
    return self.diffdict

#------------- INTERFACES -----------#
class CleanInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self.dispatch = self._base.dispatch

#------------- HOOKS --------------#
class CleanHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'clean.clean'

    self.DATA = {'hooks':  {} }    
    self.hookInfo = {}

    self.interface = interface
    self.dispatch = self.interface.dispatch

    DiffMixin.__init__(self, join(self.interface.METADATA_DIR, 'clean.md'), self.DATA)
    self._add_handler()

  def setup(self):
    for event in self.dispatch.event:
      for hook in event.hooks:
        self.hookInfo[hook.ID] = event.id
        self.DATA['hooks'].update({hook.ID: str(hook.VERSION)})

  def force(self):
    self._force_all_events()
    
  def check(self):
    return self.test_diffs()
  
  def run(self):
    self.interface.log(0, "processing clean")
    self.interface.log(1, "forcing events") 

    # if clean hook version changes, force all
    if self.handlers['hooks'].diffdict.has_key(self.ID):
      self._force_all_events()
    else:
      for hook in self.handlers['hooks'].diffdict.keys():
	      eventid = self.hookInfo[hook]
	      self._force_event(eventid)

  def apply(self):
    # every time since diffs not reported in first run scenario
    self.write_metadata()

  def _force_all_events(self):
    self.interface.log(0, "cleaning all")

    self.interface.log(1, "cleaning folder")    
    if exists(self.interface.DISTRO_DIR):
      self.interface.log(2, "cleaning '%s'" % self.interface.DISTRO_DIR)
      osutils.rm(self.interface.DISTRO_DIR, recursive=True, force=True)
      for folder in [self.interface.SOFTWARE_STORE, self.interface.METADATA_DIR]:
        osutils.mkdir(folder, parent=True)

    if not self.interface.isForced('ALL'):
      self.interface.log(1, "forcing events")
      for eventid in self.hookInfo.values():
        self._force_event(eventid)

      self.clean_metadata()
      
  def _force_event(self, eventid):
    self.__force(eventid)
    if eventid not in self.dispatch.force:
      self.dispatch.force.append(eventid)

  def __force(self, eventid):
    e = self.dispatch.get(eventid, err=True)
    if e.test(event.PROP_CAN_DISABLE):
      if not e.status:
        self.interface.log(2, "forcing %s" % eventid)        
        e.status = True
      self.interface._base.autoFC[e.id] = True
      if e.test(event.PROP_META):
        for child in e.get_children():
          self.__force(child.id)

  def _add_handler(self):
    handler = HookHandler(self.DATA['hooks'])
    self.DT.addHandler(handler)
    self.handlers['hooks'] = handler
    
