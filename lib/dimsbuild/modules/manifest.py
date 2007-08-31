""" 
manifest.py

Provides information about files included in the distribution.  
"""

import csv

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.1

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
    
    self.mfile = self.interface.SOFTWARE_STORE/'.manifest'
    
    self.DATA =  {
      'input':  [],
      'output': [self.mfile],
    }
    self.mdfile = self.interface.METADATA_DIR/'manifest.md'
  
  def setup(self):
    self.filesdata = [ i for i in \
                       self.interface.SOFTWARE_STORE.findpaths() \
                       if i != self.mfile and not i.isdir() ]
    self.DATA['input'].extend(self.filesdata)
    self.interface.setup_diff(self.mdfile, self.DATA)
  
  def check(self):
    return self.interface.test_diffs()
  
  def clean(self):
    self.interface.log(0, "cleaning manifest event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
  
  def run(self):
    self.interface.log(0, "generating manifest")
    self.interface.remove_output(all=True)
    
    # set manifest data
    manifest = []
    for i in self.filesdata:
      if i not in self.DATA['output']:
        st = i.stat()
        manifest.append({
          'file':  i[len(self.interface.SOFTWARE_STORE)+1:],
          'size':  st.st_size,
          'mtime': st.st_mtime,
        })
    manifest.sort()
    
    # generate manifest
    self.mfile.touch()
    mf = self.mfile.open('w')
    mwriter = csv.DictWriter(mf, FIELDS, lineterminator='\n')
    for line in manifest:
      mwriter.writerow(line)
    mf.close()
    
    # set global variable
    self.interface.cvars['manifest-changed'] = True
    
    # update metadata
    self.interface.write_metadata()
