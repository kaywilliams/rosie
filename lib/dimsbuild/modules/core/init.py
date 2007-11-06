from dimsbuild.event   import Event, CLASS_META, PROTECT_SKIP, PROTECT_ENABLED
from dimsbuild.logging import L1

API_VERSION = 5.0
EVENTS = {'ALL': ['InitEvent', 'SetupEvent']}

class InitEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'init',
      properties = PROTECT_SKIP | PROTECT_ENABLED,
      provides = ['option-parser'],
    )
  
  def clean(self):
    if self.METADATA_DIR.exists():
      self.log(2, L1("cleaning '%s'" % self.METADATA_DIR))
      self.METADATA_DIR.rm(recursive=True)
  
  def apply(self):
    for folder in [self.TEMP_DIR, self.METADATA_DIR]:
      if not folder.exists():
        self.log(2, L1("making directory '%s'" % folder))
        folder.mkdirs()

class SetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'setup',
      properties = CLASS_META,
      comes_after = ['init'],
      conditionally_comes_after = ['autoclean'],
    )
