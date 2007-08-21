""" 
manifest.py

Provides information about files included in the distribution.  
"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftware.com>, \
               Kay Williams <kwilliams@abodiosoftware.com>"
__version__ = "1.0"
__date__    = "August 3th, 2007"

import csv
import os

from os.path import join, exists

from dims import osutils

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'manifest',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['manifest-changed'],
    'conditional-requires': ['MAIN'],
    'parent': 'ALL',
  },
]

HOOK_MAPPING = {
  'ManifestHook': 'manifest',
}

FIELDS = ['file', 'size', 'mtime']

#------ HOOKS ------#
class ManifestHook:
  def __init__(self, interface):
    self.VERSION = 2
    self.ID = 'manifest'
    
    self.interface = interface
    
    self.mfile = join(self.interface.SOFTWARE_STORE, '.manifest')

    self.DATA =  {
      'input':  [],
      'output': [self.mfile],
    }
  
  def setup(self):
    files = []
    for file in osutils.find(self.interface.SOFTWARE_STORE):
      if file != self.mfile and file != self.interface.SOFTWARE_STORE :
        files.append(file)

    self.DATA['input'].extend(files)
    self.interface.setup_diff(join(self.interface.METADATA_DIR, 'manifest.md'), self.DATA)

  def check(self):
    return self.interface.test_diffs()

  def clean(self):
    osutils.rm(self.interface.handlers['output'].oldoutput.keys(), force=True)
    self.interface.clean_metadata()
  
  def run(self):
    self.interface.log(0, "generating manifest")
    if not self.interface.has_changed('input'):
      return 

    #get file stat data (reuse from difftest)
    manifest = []
    for file in self.interface.handlers['input'].newinput.keys():
      size,mtime = self.interface.handlers['input'].newinput[file]
      file = file[len(self.interface.SOFTWARE_STORE)+1:]
      if file != '/.manifest':
        manifest.append({'file':  file,
                         'size':  size,
                         'mtime': mtime})
    manifest.sort()

    #generate manifest    
    osutils.rm(self.interface.handlers['output'].oldoutput.keys(), force=True)
    if exists(self.mfile):
      osutils.rm(self.mfile, force=True) #### FIXME
    os.mknod(self.mfile)
    mf = open(self.mfile, 'w')
    mwriter = csv.DictWriter(mf, FIELDS, lineterminator='\n')
    for line in manifest:
      mwriter.writerow(line)
    mf.close()

    #set global variable
    self.interface.cvars['manifest-changed'] = True

  def apply(self):
    #Update metadata
    self.interface.write_metadata()

