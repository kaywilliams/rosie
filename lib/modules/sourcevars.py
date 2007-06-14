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

from event     import EVENT_TYPE_PROC
from interface import EventInterface
from locals    import L_BUILDSTAMP_FORMAT, L_IMAGES
from main      import BOOLEANS_TRUE, locals_imerge
from callback  import BuildSyncCallback

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'source-vars',
    'interface': 'SourcevarsInterface',
    'provides': ['source-vars'],
    'requires': ['anaconda-version'],
    'properties': EVENT_TYPE_PROC
  },
]

HOOK_MAPPING = {
  'SourcevarsHook': 'source-vars',
}

#------ INTERFACES ------#
class SourcevarsInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
  def setSourceVars(self, vars):
    self._base.source_vars = vars

#------ HOOKS ------#
class SourcevarsHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sourcevars.source-vars'
    
    self.interface = interface
    self.vars = self.interface.BASE_VARS

    self.callback = BuildSyncCallback(interface.logthresh)

  def run(self):
    #Setup
    i,s,n,d,u,p = self.interface.getStoreInfo(self.interface.getBaseStore())
    d = d.lstrip('/') # un-absolute d
    source_initrd_file = self.interface.storeInfoJoin(s, n, join(d, 'isolinux/initrd.img'))
    cache_initrd_file = join(self.interface.INPUT_STORE, i, d, 'isolinux/initrd.img')

    #Download initrd.img to cache
    osutils.mkdir(osutils.dirname(cache_initrd_file), parent=True)
    #sync.sync(source_initrd_file, osutils.dirname(cache_initrd_file), username=u, password=p)
    self.interface.cache(join(d, 'isolinux/initrd.img'), prefix=i, callback=self.callback)

    #Extract buildstamp
    locals = locals_imerge(L_IMAGES, self.interface.cvars['anaconda-version'])
    image  = locals.get('//images/image[@id="initrd.img"]')
    format = image.get('format/text()')
    zipped = image.get('zipped/text()', 'False') in BOOLEANS_TRUE
    self.image = imglib.Image(cache_initrd_file, format, zipped)
    self.image.open()
    sourcevars = self.image.read('.buildstamp')

    #Parse buildstamp
    locals = locals_imerge(L_BUILDSTAMP_FORMAT, self.interface.cvars['anaconda-version'])
    buildstamp_fmt = locals.get('//buildstamp-format')
    buildstamp = ffile.XmlToFormattedFile(buildstamp_fmt)
    sourcevars = buildstamp.floread(self.image.read('.buildstamp'))

    #Update source_vars
    self.interface.cvars['source-vars'] = sourcevars

  def error(self, e):
    try:
      self.close()
    except:
      pass
