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
