from dims.dispatch import PROPERTY_META

from dimsbuild.event import Event

API_VERSION = 5.0

class RpmsEvent(Event):
  def __init__(self):
    Event.__init__(self,
                   id='RPMS',
                   properties=PROPERTY_META)

    self.cvars['rpms-source']  = self.METADATA_DIR/'rpms-src'
    self.cvars['custom-rpms']  = []
    self.cvars['custom-srpms'] = []

MODULES = [
  'config',
  'default_theme',
  'localrepo',
  'logos',
  'release',
]

EVENTS = {'ALL': [RpmsEvent]}
