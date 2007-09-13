import csv

from dimsbuild.event import Event

API_VERSION = 5.0

FIELDS = ['file', 'size', 'mtime']

class ManifestEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'manifest',
      provides = ['manifest-changed'],
      comes_after = ['MAIN'],
    )
    
    self.mfile = self.SOFTWARE_STORE/'.manifest'
    
    self.DATA =  {
      'input':  [],
      'output': [self.mfile],
    }
    
    self.mdfile = self.get_mdfile()
  
  def _setup(self):
    self.filesdata = [ i for i in \
                       self.SOFTWARE_STORE.findpaths() \
                       if i != self.mfile and not i.isdir() ]
    self.DATA['input'].extend(self.filesdata)
    self.setup_diff(self.mdfile, self.DATA)
  
  def _check(self):
    return self.test_diffs()
  
  def _clean(self):
    self.remove_output(all=True)
    self.clean_metadata()
  
  def _run(self):
    self.log(0, "generating manifest")
    self.remove_output(all=True)
    
    # set manifest data
    manifest = []
    for i in self.filesdata:
      if i not in self.DATA['output']:
        st = i.stat()
        manifest.append({
          'file':  i[len(self.SOFTWARE_STORE)+1:],
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
    self.cvars['manifest-changed'] = True
    
    # update metadata
    self.write_metadata()


EVENTS = {'ALL': [ManifestEvent]}
