from os.path import exists, join

from dims         import filereader
from dims.osutils import find, mkdir

from event    import EVENT_TYPE_META
from main     import BOOLEANS_TRUE
from rpms.lib import RpmsInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'RPMS',
    'provides': ['RPMS'],
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_META,
    'requires': ['stores'],
  },
]

MODULES = [
  'config',
  'default_theme',
  'logos',  
  'release',
]

STORE_XML = ''' 
<store id="dimsbuild-local">
  <path>file://%s</path>
</store>
'''

SOURCE_XML = ''' 
<store id="dimsbuild-local-srpms">
  <path>file://%s</path>
</store>
'''

HOOK_MAPPING = {
  'LocalStoresHook'  : 'stores',
  'LocalSrpmsHook'   : 'source',
  'RpmsHook'         : 'RPMS',
  'LocalRepogenHook' : 'repogen',
}

class LocalStoresHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.__init__.stores'
    self.interface = interface
    
  def pre(self):
    localrepo = join(self.interface.METADATA_DIR, 'localrepo/')
    mkdir(localrepo)
    self.interface.add_store(STORE_XML % localrepo)

class LocalSrpmsHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.__init__.source'
    self.interface = interface

  def pre(self):
    if self.interface.config.get('//source/include/text()', 'False') in BOOLEANS_TRUE:
      store = join(self.interface.METADATA_DIR, 'localrepo/SRPMS/')
      self.interface.add_store(SOURCE_XML % store)

class RpmsHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.__init__.RPMS'
    self.interface = interface

  def post(self):    
    self.interface.createrepo()
    pkgs = find(location=self.interface.LOCAL_REPO, name='*[Rr][Pp][Mm]', prefix=False)
    if len(pkgs) > 0:
      filereader.write(pkgs, join(self.interface.METADATA_DIR, 'dimsbuild-local.pkgs'))
    storesinfo = self.interface.get_cvar('input-store-lists')
    storesinfo.update({'dimsbuild-local': pkgs})
    self.interface.set_cvar('input-stores-list', storesinfo)    

class LocalRepogenHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.__init__.repogen'
    self.interface = interface

  def post(self):
    cfgfile = self.interface.get_cvar('repoconfig-file', None)
    if cfgfile is None: return  
    lines = filereader.read(cfgfile)
    lines.append('[dimsbuild-local]')
    lines.append('name = dimsbuild-local')
    lines.append('baseurl = file://%s' % join(self.interface.METADATA_DIR, 'localrepo/'))  
    filereader.write(lines, cfgfile)
