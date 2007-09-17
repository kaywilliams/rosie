""" 
files.py

Includes user-provided files and folders within the distribution folder.
"""

from dimsbuild.event import Event

API_VERSION = 5.0


class FilesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'files',
    )
    
    self.DATA =  {
      'config': ['/distro/files'],
      'input':  [],
      'output': [],
    }
  
  def _validate(self):
    self.validate('/distro/files', 'files.rng')
  
  def _setup(self):
    self.setup_diff(self.DATA)
    self.setup_sync(self.SOFTWARE_STORE,
                    xpaths=['/distro/files/path'])
  
  def _run(self):
    self.log(0, "processing user-provided files")
    # delete altered files
    self.remove_output()
          
    # download input files
    self.sync_input()
    
    self.write_metadata()

EVENTS = {'MAIN': [FilesEvent]}
