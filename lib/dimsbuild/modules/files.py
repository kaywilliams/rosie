""" 
files.py

Includes user-provided files and folders within the distribution folder.
"""

__author__  = 'Kay Williams <kwilliams@abodiosoftware.com>'
__version__ = '1.0'
__date__    = 'June 29th, 2007'

import os

from os.path      import join, exists, dirname, basename, isdir
from ConfigParser import ConfigParser

from dims import osutils
from dims import sync

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from dimsbuild.modules.lib import DiffMixin, FilesMixin

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

class FilesHook(DiffMixin, FilesMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'files.files'    
    self.interface = interface

    self.DATA =  {
      'config':    ['/distro/files'],
      'input':     [],
      'output':    [],
    }

    DiffMixin.__init__(self, join(self.interface.METADATA_DIR, 'files.md'), self.DATA)
    FilesMixin.__init__(self, self.interface.SOFTWARE_STORE)

  def pre(self):
    if self.interface.config.xpath('/distro/files/path/text()', []):
      self.interface.log(0, "processing user-provided files")
    elif self.handlers['output'].oldoutput.keys():
      self.interface.log(0, "removing previously-provided files")
      
  def setup(self):
    # add files to the input and output filelists - look at FilesMixin.add_files() in interface.py
    self.add_files(xpaths='/distro/files/path')
    
  def clean(self):
    self.remove_files(self.handlers['output'].oldoutput.keys())
    self.clean_metadata()

  def check(self):
    return self.test_diffs()

  def run(self):
    if not self.interface.isForced('files'):
      # delete the files that have been modified or aren't required anymore
      self.remove_files()
          
    # download the files
    self.sync_files()
    
  def apply(self):
    self.write_metadata()
