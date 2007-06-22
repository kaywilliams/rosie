from os.path import exists, join

from dims         import filereader
from dims.osutils import find, mkdir, rm

import dims.listcompare as listcompare

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
    
  def post(self):
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
    pkgsfile = join(self.interface.METADATA_DIR, 'dimsbuild-local.pkgs')    
    old = filereader.read(pkgsfile)
    
    current = find(location=self.interface.LOCAL_REPO, name='*[Rr][Pp][Mm]', prefix=False)
    l,r,_ = listcompare.compare(old, current)
    
    if l or r:
      self.interface.createrepo()
      self.interface.cvars['input-store-changed'] = True
      
      # HACK ALERT: need to the remove the .depsolve/dimsbuild-local folder so
      # that depsolver picks up the new RPM.
      rm(join(self.interface.METADATA_DIR, '.depsolve/dimsbuild-local'),
         recursive=True, force=True)
    
      filereader.write(current, pkgsfile)
      storesinfo = self.interface.cvars['input-store-lists'].update({'dimsbuild-local': current})

class LocalRepogenHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.__init__.repogen'
    self.interface = interface

  def post(self):
    if not self.interface.cvars['repoconfig-file']: return
    lines = filereader.read(self.interface.cvars['repoconfig-file'])
    lines.append('[dimsbuild-local]')
    lines.append('name = dimsbuild-local')
    lines.append('baseurl = file://%s' % join(self.interface.METADATA_DIR, 'localrepo/'))
    filereader.write(lines, self.interface.cvars['repoconfig-file'])
