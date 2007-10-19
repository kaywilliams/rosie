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
      'config': ['.'],
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.setup_sync(self.SOFTWARE_STORE, xpaths=['path'])

  def run(self):
    self.log(0, L0("processing user-provided files"))
    self.io.sync_input(cache=True)
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()

  def error(self, e):
    # performing a subset of Event.error since sync handles partially downloaded files
    if self.mdfile.exists():
      (self.mddir / '.debug').mkdir()
      self.mdfile.rename(self.mddir/'.debug'/self.mdfile.basename)

EVENTS = {'OS': [FilesEvent]}
