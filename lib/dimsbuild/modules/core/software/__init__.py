from dimsbuild.event import Event, CLASS_META

API_VERSION = 5.0
EVENTS = {'OS': ['SoftwareMetaEvent']}

class SoftwareMetaEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'software',
      properties = CLASS_META,
      provides = ['os-content'],
    )
