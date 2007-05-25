from event     import EVENT_TYPE_META
from interface import EventInterface, FlowControlRWMixin

API_VERSION = 3.0

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
    'requires': ['init'],
    'parent': 'ALL',
  },
  {
    'id': 'validate',
    'interface': 'ValidateInterface',
    'provides': ['validate'],
    'requires': ['applyopt'],
    'parent': 'ALL',
  },
  {
    'id': 'MAIN',
    'provides': ['MAIN'],
    'requires': ['init', 'applyopt'],
    'parent': 'ALL',
    'properties': EVENT_TYPE_META,
  },
]

class InitInterface(EventInterface):
  def __init__(self, base, parser):
    EventInterface.__init__(self, base)
    self.parser = parser
  
  def getOptParser(self, groupid):
    for group in self.parser.option_groups:
      if group.id == groupid:
        return group
    return self.parser

class ApplyOptInterface(EventInterface, FlowControlRWMixin):
  def __init__(self, base, options):
    EventInterface.__init__(self, base)
    FlowControlRWMixin.__init__(self, options)
    self.options = options

class ValidateInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)

def validate_hook(interface):
  "Perform preprocess validation"
  interface.log(0, "performing preprocess validation")
