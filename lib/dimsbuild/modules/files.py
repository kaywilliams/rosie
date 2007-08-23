""" 
files.py

Includes user-provided files and folders within the distribution folder.
"""

__author__  = 'Kay Williams <kwilliams@abodiosoftware.com>'
__version__ = '1.0'
__date__    = 'June 29th, 2007'

from os.path import join

from dims import osutils

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'files',
    'parent': 'MAIN',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'FilesHook': 'files',
  'ValidateHook': 'validate',
}

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'files.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/files', 'files.rng')

class FilesHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'files.files'    
    self.interface = interface

    self.DATA =  {
      'config': ['/distro/files'],
      'input':  [],
      'output': [],
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'files.md')

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    i,o = self.interface.setup_sync(
      xpaths=[('/distro/files/path',
               osutils.dirname(self.interface.config.file),
               self.interface.SOFTWARE_STORE)]
    )
    self.DATA['input'].extend(i)
    self.DATA['output'].extend(o)
    
  def clean(self):
    self.interface.log(0, "cleaning files event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()

  def run(self):
    self.interface.log(0, "processing user-provided files")
    # delete altered files
    self.interface.remove_output()
          
    # download input files
    self.interface.sync_input()
    
    self.interface.write_metadata()
