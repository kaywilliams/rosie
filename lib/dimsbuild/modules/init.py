from dims.CleanHelpFormatter import OptionGroupId

from dimsbuild.event     import EVENT_TYPE_META
from dimsbuild.interface import EventInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'init',
    'interface': 'InitInterface',
    'provides': ['option-parser'],
    'parent': 'ALL',
  },
  {
    'id': 'applyopt',
    'interface': 'ApplyOptInterface',
    'requires': ['option-parser'],
    'conditional-requires': ['init'],
    'parent': 'ALL',
  },
  {
    'id': 'MAIN',
    'conditional-requires': ['init', 'applyopt', 'validate', 'clean'],
    'parent': 'ALL',
    'properties': EVENT_TYPE_META,
  },
]

HOOK_MAPPING = {
  'InitHook': 'init',
}


class InitInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self.parser = None
  
  def getOptParser(self, groupid=None):
    if groupid is None:
      return self.parser    
    for group in self.parser.option_groups:
      if group.id == groupid:
        return group
      
    # at this point, the groupid is not there in option_groups
    # list; add it and return the pointer to it
    group = OptionGroupId(self.parser, "Configuration file validation options", groupid)
    self.parser.add_option_group(group)
    return group

class ApplyOptInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self.options = None


class InitHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'init.init'    
    self.interface = interface
  
  def run(self):
    for folder in [self.interface.TEMP_DIR, self.interface.SOFTWARE_STORE,
                   self.interface.METADATA_DIR]:
      if not folder.exists():
        self.interface.log(2, "Making directory '%s'" % folder)
        folder.mkdirs()
