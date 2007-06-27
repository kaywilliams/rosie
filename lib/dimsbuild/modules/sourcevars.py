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
from dims import imglib

from dimsbuild.callback  import BuildSyncCallback
from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_PROC
from dimsbuild.locals    import L_BUILDSTAMP_FORMAT, L_IMAGES
from dimsbuild.misc      import locals_imerge

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'source-vars',
    'provides': ['source-vars'],
    'requires': ['anaconda-version'],
    'properties': EVENT_TYPE_PROC
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
  
  def error(self, e):
    try:
      self.image.close()
      self.image.cleanup()
    except:
      pass
  
  def run(self):
    self.interface.log(0, "computing source variables")
    #Setup
    info = self.interface.getStoreInfo(self.interface.getBaseStore())
    
    #Download initrd.img to cache
    initrd_file = join(self.interface.INPUT_STORE, info.id,
                       self.interface.cache(info.id, 'isolinux/initrd.img',
                         username=info.username, password=info.password,
                         callback=BuildSyncCallback(self.interface.logthresh)))
    
    # because imglib isn't very good at preserving timestamps when it should be,
    # we make a copy before opening and reading
    initrd_file2 = '%s2' % initrd_file #!
    osutils.cp(initrd_file, initrd_file2) #!
    
    #Extract buildstamp
    locals = locals_imerge(L_IMAGES, self.interface.cvars['anaconda-version'])
    image  = locals.get('//images/image[@id="initrd.img"]')
    format = image.get('format/text()')
    zipped = image.get('zipped/text()', 'False') in BOOLEANS_TRUE
    self.image = imglib.Image(initrd_file2, format, zipped) #!
    self.image.open('r')
    sourcevars = self.image.read('.buildstamp')
    
    #Parse buildstamp
    locals = locals_imerge(L_BUILDSTAMP_FORMAT, self.interface.cvars['anaconda-version'])
    buildstamp_fmt = locals.get('//buildstamp-format')
    buildstamp = ffile.XmlToFormattedFile(buildstamp_fmt)
    sourcevars = buildstamp.floread(self.image.read('.buildstamp'))
    
    #Update source_vars
    self.interface.cvars['source-vars'] = sourcevars

    #Cleanup
    self.image.close()
    self.image.cleanup()
    
    osutils.rm(initrd_file2, force=True) #!
