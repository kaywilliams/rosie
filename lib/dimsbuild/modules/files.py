""" 
files.py

Includes user-provided files and folders within the distribution folder.
"""

from dimsbuild.event   import Event
from dimsbuild.logging import L0

API_VERSION = 5.0


class FilesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'files',
      provides = ['os-contents'],
    )
    
    self.DATA =  {
      'config': ['/distro/files'],
      'input':  [],
      'output': [],
    }
  
  def validate(self):
    self.validator.validate('/distro/files', 'files.rng')
  
  def setup(self):
    self.diff.setup(self.DATA)
    self.io.setup_sync(self.SOFTWARE_STORE, xpaths=['/distro/files/path'])
  
  def run(self):
    self.log(0, L0("processing user-provided files"))
    self.io.sync_input()
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()

EVENTS = {'OS': [FilesEvent]}
