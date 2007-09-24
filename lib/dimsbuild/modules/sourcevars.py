""" 
sourcevars.py

provides information about the source distribution 
"""

from dims import FormattedFile as ffile
from dims import img

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event, RepoMixin #!
from dimsbuild.logging   import L0

API_VERSION = 5.0

class SourceVarsEvent(Event, RepoMixin): #!
  def __init__(self):
    Event.__init__(self,
      id = 'source-vars',
      provides = ['source-vars'],
      requires = ['anaconda-version'],
    )
    
    self.DATA =  {
      'input':     [],
      'output':    [],
    }
  
  def error(self, e):
    try:
      self.image.close()
      self.image.cleanup()
    except:
      pass
  
  def setup(self):
    self.diff.setup(self.DATA)
    
    initrd_in=self.getRepo(self.getBaseRepoId()).rjoin('isolinux/initrd.img')
    
    self.io.setup_sync(self.mddir, id='initrd.img', paths=[initrd_in])
    self.initrd_out = self.io.list_output(what='initrd.img')[0]
    
    self.buildstamp_out = self.mddir/'.buildstamp'
    
    self.DATA['output'].append(self.buildstamp_out)
  
  def run(self):
    self.log(0, L0("computing source variables"))
    
    # download input files
    self.io.sync_input()
    
    # extract buildstamp
    image = self.locals.files['isolinux']['initrd.img']
    self.image = img.MakeImage(self.initrd_out, image['format'], image.get('zipped', False))
    self.image.open('r')
    self.image.read('.buildstamp', self.mddir)
    self.image.close()
    img.cleanup()
    
    # update metadata
    self.diff.write_metadata()
      
  def apply(self):
    # parse buildstamp
    buildstamp = ffile.DictToFormattedFile(self.locals.buildstamp_fmt)
    sourcevars = buildstamp.read(self.buildstamp_out)
    
    # update source_vars
    self.cvars['source-vars'] = sourcevars

EVENTS = {'MAIN': [SourceVarsEvent]}
