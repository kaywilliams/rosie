from dimsbuild.event import Event, CLASS_META

API_VERSION = 5.0
EVENTS = {'software': ['RpmsEvent']}

class RpmsEvent(Event):
  def __init__(self):
    Event.__init__(self,
                   id='rpms',
                   properties=CLASS_META)

    self.cvars['custom-rpms']  = []
    self.cvars['custom-srpms'] = []
