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

from dimsbuild import difftest

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
    self.mdfile = join(self.interface.METADATA_DIR, 'manifest.md')
  
  def setup(self):
    self.filesdata = [ (i,s,m) for i,s,m in \
                       difftest.getFileList(self.interface.SOFTWARE_STORE) \
                       if i != self.mfile ]
    self.DATA['input'].extend(self.filesdata)
    self.interface.setup_diff(self.mdfile, self.DATA)

  def check(self):
    return self.interface.test_diffs()

  def clean(self):
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
  
  def run(self):
    self.interface.log(0, "generating manifest")
    self.interface.remove_output(all=True)
    
    # set manifest data
    manifest = []
    for i,s,m in self.filesdata:
      if i not in self.DATA['output']:
        manifest.append({
          'file':  i[len(self.interface.SOFTWARE_STORE)+1:],
          'size':  s,
          'mtime': m,
        })
    manifest.sort()

    # generate manifest    
    os.mknod(self.mfile)
    mf = open(self.mfile, 'w')
    mwriter = csv.DictWriter(mf, FIELDS, lineterminator='\n')
    for line in manifest:
      mwriter.writerow(line)
    mf.close()

    # set global variable
    self.interface.cvars['manifest-changed'] = True

  def apply(self):
    # update metadata
    self.interface.write_metadata()

