from spin.event   import Event, CLASS_META
from spin.logging import L1

API_VERSION = 5.0
EVENTS = {'ALL': ['InitEvent', 'SetupEvent', 'OSMetaEvent']}

class InitEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'init',
      provides = ['option-parser'],
      suppress_run_message = True
    )

  def clean(self):
    if self.METADATA_DIR.exists():
      self.log(2, L1("cleaning '%s'" % self.METADATA_DIR))
      self.METADATA_DIR.rm(recursive=True)

  def apply(self):
    for folder in [self.TEMP_DIR, self.METADATA_DIR]:
      if not folder.exists():
        self.log(4, L1("making directory '%s'" % folder))
        folder.mkdirs()

  def verify_directories_exist(self):
    "output directories exist"
    for folder in [self.TEMP_DIR, self.METADATA_DIR]:
      self.verifier.failUnless(folder.exists(), "folder '%s' does not exist" % folder)

class SetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'setup',
      properties = CLASS_META,
      comes_after = ['init'],
      conditionally_comes_after = ['autoclean'],
      suppress_run_message = True
    )

class OSMetaEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'OS',
      properties = CLASS_META,
      comes_after = ['setup'],
      suppress_run_message = True
    )
