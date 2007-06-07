from event     import EVENT_TYPE_META
from interface import EventInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'init',
    'interface': 'InitInterface',
    'provides': ['init'],
    'parent': 'ALL',
  },
  {
    'id': 'applyopt',
    'interface': 'ApplyOptInterface',
    'provides': ['applyopt'],
    'conditional-requires': ['init'],
    'parent': 'ALL',
  },
  {
    'id': 'validate',
    'provides': ['validate'],
    'conditional-requires': ['applyopt'],
    'parent': 'ALL',
  },
  {
    'id': 'MAIN',
    'provides': ['MAIN'],
    'conditional-requires': ['init', 'applyopt', 'validate'],
    'parent': 'ALL',
    'properties': EVENT_TYPE_META,
  },
]

HOOK_MAPPING = {
  'ValidateHook': 'validate',
}


class InitInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self.parser = None
  
  def getOptParser(self, groupid):
    for group in self.parser.option_groups:
      if group.id == groupid:
        return group
    return self.parser

class ApplyOptInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self.options = None

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'init.validate'
    
    self.interface = interface
  
  def run(self):
    self.interface.log(0, "performing preprocess validation")
