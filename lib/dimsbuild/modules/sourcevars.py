""" 
sourcevars.py

provides information about the source distribution 
"""

__author__  = "Kay Williams <kwilliams@abodiosoftware.com>"
__version__ = "1.0"
__date__    = "June 5th, 2007"

from os.path  import join, exists

from dims import FormattedFile as ffile
from dims import osutils
from dims import sync
from dims import img

from dimsbuild.callback  import BuildSyncCallback
from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.locals    import L_BUILDSTAMP_FORMAT, L_IMAGES
from dimsbuild.misc      import locals_imerge
from dimsbuild.interface import DiffMixin

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'source-vars',
    'provides': ['source-vars'],
    'requires': ['anaconda-version'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'SourcevarsHook': 'source-vars',
}


#------ HOOKS ------#
class SourcevarsHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sourcevars.source-vars'
    
    self.interface = interface

    self.DATA =  {
      'input':     [],
      'output':    [],
    }

    self.md_dir = join(self.interface.METADATA_DIR, 'sourcevars/')

    DiffMixin.__init__(self, join(self.md_dir, 'sourcevars.md'), self.DATA)
  
  def error(self, e):
    try:
      self.image.close()
      self.image.cleanup()
    except:
      pass

  def setup(self):
    self.repo = self.interface.getRepo(self.interface.getBaseRepoId())
    self.infile = self.repo.rjoin('isolinux/initrd.img')
    self.outfile = join(self.md_dir, '.buildstamp')

    self.update({'input':  [ self.infile ],
                 'output': [ self.outfile ]
    })

  def check(self):
    return self.test_diffs()    

  def force(self):
    osutils.rm(self.handlers['output'].oldoutput.keys(), force=True)
    self.clean_metadata()

  def run(self):
    self.interface.log(0, "computing source variables")
        
    #Download initrd.img to cache
    initrd_file = self.interface.cache(self.repo, 'isolinux/initrd.img',
                  username=self.repo.username, password=self.repo.password,
                  callback=BuildSyncCallback(self.interface.logthresh))
    
    #Extract buildstamp
    locals = locals_imerge(L_IMAGES, self.interface.cvars['anaconda-version'])
    image  = locals.get('//images/image[@id="initrd.img"]')
    format = image.get('format/text()')
    zipped = image.get('zipped/text()', 'False') in BOOLEANS_TRUE
    self.image = img.MakeImage(initrd_file, format, zipped)
    self.image.open('r')
    self.image.read('.buildstamp', self.md_dir)
    self.image.close()
    img.cleanup()

    #Update metadata
    self.write_metadata()
    
  def apply(self):
    #Parse buildstamp
    locals = locals_imerge(L_BUILDSTAMP_FORMAT, self.interface.cvars['anaconda-version'])
    buildstamp_fmt = locals.get('//buildstamp-format')
    buildstamp = ffile.XmlToFormattedFile(buildstamp_fmt)
    sourcevars = buildstamp.read(self.outfile)
    
    #Update source_vars
    self.interface.cvars['source-vars'] = sourcevars
