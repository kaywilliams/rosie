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

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.locals    import L_BUILDSTAMP_FORMAT, L_IMAGES
from dimsbuild.misc      import locals_imerge

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
class SourcevarsHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sourcevars.source-vars'
    
    self.interface = interface

    self.DATA =  {
      'input':     [],
      'output':    [],
    }

    self.md_dir = join(self.interface.METADATA_DIR, 'sourcevars/')
  
  def error(self, e):
    try:
      self.image.close()
      self.image.cleanup()
    except:
      pass

  def setup(self):
    self.interface.setup_diff(join(self.md_dir, 'sourcevars.md'), self.DATA)

    initrd_in=self.interface.getRepo(self.interface.getBaseRepoId()).rjoin('isolinux/initrd.img')

    i,o = self.interface.getFileLists( paths=[(initrd_in, self.md_dir)] )

    #TODO remove after list_output is fixed
    for item in o:
      dest,src = item
      self.initrd_out=dest
      break

    self.buildstamp_out = join(self.md_dir, '.buildstamp')

    self.DATA['input'].extend(i)
    self.DATA['output'].extend(o)
    self.DATA['output'].append(self.buildstamp_out)

    # TODO uncomment after list_output is fixed
    #self.initrd_out=self.interface.list_output( initrd_in )
   
  def check(self):
    return self.interface.test_diffs()

  def clean(self):
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def run(self):
    self.interface.log(0, "computing source variables")
        
    # download input files
    self.interface.sync_input()
    
    #Extract buildstamp
    locals = locals_imerge(L_IMAGES, self.interface.cvars['anaconda-version'])
    image  = locals.get('//images/image[@id="initrd.img"]')
    format = image.get('format/text()')
    zipped = image.get('zipped/text()', 'False') in BOOLEANS_TRUE
    self.image = img.MakeImage(self.initrd_out, format, zipped)
    self.image.open('r')
    self.image.read('.buildstamp', self.md_dir)
    self.image.close()
    img.cleanup()

    #Update metadata
    self.interface.write_metadata()
        
  def apply(self):
    #Parse buildstamp
    locals = locals_imerge(L_BUILDSTAMP_FORMAT, self.interface.cvars['anaconda-version'])
    buildstamp_fmt = locals.get('//buildstamp-format')
    buildstamp = ffile.XmlToFormattedFile(buildstamp_fmt)
    sourcevars = buildstamp.read(self.buildstamp_out)
    
    #Update source_vars
    self.interface.cvars['source-vars'] = sourcevars
