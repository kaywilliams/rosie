from dims.dispatch import PROPERTY_META

from dimsbuild.event import Event

API_VERSION = 5.0

class RpmsEvent(Event):
  def __init__(self):
    Event.__init__(self,
                   id='rpms',
                   properties=PROPERTY_META)

    self.cvars['custom-rpms']  = []
    self.cvars['custom-srpms'] = []

EVENTS = {'software': [RpmsEvent]}
