import csv

from dimsbuild.event   import Event
from dimsbuild.logging import L0

API_VERSION = 5.0

FIELDS = ['file', 'size', 'mtime']

class ManifestEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'manifest',
      requires = ['composed-tree'],
      provides = ['manifest-file'],
      comes_after = ['MAIN'],
    )
    
    self.DATA =  {
      'input':  [],
      'output': [],
    }
    
    self.output_dir = self.DISTRO_DIR/'output'
    
  def setup(self):
    self.mfile = self.mddir/'.manifest'
    self.DATA['output'].append(self.mfile)
    
    self.filesdata = [ i for i in \
                       self.output_dir.findpaths() \
                       if i != self.mfile and not i.isdir() ]
    self.DATA['input'].extend(self.filesdata)
    self.diff.setup(self.DATA)
  
  def run(self):
    self.log(0, L0("generating manifest"))
    self.io.remove_output(all=True)
    
    # set manifest data
    manifest = []
    for i in self.filesdata:
      if i not in self.DATA['output']:
        st = i.stat()
        manifest.append({
          'file':  i[len(self.output_dir)+1:],
          'size':  st.st_size,
          'mtime': st.st_mtime,
        })
    manifest.sort()
    
    # generate manifest
    self.mfile.dirname.mkdirs()
    self.mfile.touch()
    mf = self.mfile.open('w')
    mwriter = csv.DictWriter(mf, FIELDS, lineterminator='\n')
    for line in manifest:
      mwriter.writerow(line)
    mf.close()
   
    # update metadata
    self.diff.write_metadata()
  
  def apply(self):
    self.cvars['manifest-file'] = self.mfile

EVENTS = {'ALL': [ManifestEvent]}
