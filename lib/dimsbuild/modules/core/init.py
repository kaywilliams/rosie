from dims.dispatch import PROPERTY_META, PROPERTY_PROTECTED

from dimsbuild.event   import Event
from dimsbuild.logging import L2

API_VERSION = 5.0

class InitEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'init',
      properties = PROPERTY_PROTECTED,
      provides = ['option-parser'],
    )
  
  def clean(self):
    if self.CACHE_DIR.exists():
      self.log(2, L2("cleaning '%s'" % self.CACHE_DIR))
      self.CACHE_DIR.rm(recursive=True)
  
  def run(self):
    for folder in [self.TEMP_DIR, self.METADATA_DIR]:
      if not folder.exists():
        self.log(2, L2("Making directory '%s'" % folder))
        folder.mkdirs()

class SetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'SETUP',
      properties = PROPERTY_META,
      comes_after = ['init'],
      conditionally_comes_after = ['validate', 'autoclean'],
    )


EVENTS = {'ALL': [InitEvent, SetupEvent]}
