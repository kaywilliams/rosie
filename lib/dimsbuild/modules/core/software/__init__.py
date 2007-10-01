from dims.dispatch import PROPERTY_META

from dimsbuild.event import Event

API_VERSION = 5.0

class SoftwareMetaEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'SOFTWARE',
      properties = PROPERTY_META,
      provides = ['os-content'],
    )

EVENTS = {'OS': [SoftwareMetaEvent]}
