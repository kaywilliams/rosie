from os.path import exists, join

from dims         import filereader
from dims.osutils import find, mkdir, rm

import dims.listcompare as listcompare

from event     import EVENT_TYPE_META
from interface import RepoContentMixin
from main      import BOOLEANS_TRUE

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
<store id="localrepo">
  <path>file://%s</path>
</store>
'''

SOURCE_XML = ''' 
<store id="localrepo-srpms">
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

class RpmsHook(RepoContentMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.__init__.RPMS'
    self.interface = interface

    RepoContentMixin.__init__(self, mdstores=self.interface.METADATA_DIR)

  def post(self):
    createrepo = True
    if not exists(join(self.mdstores, 'localrepo', 'repodata')):
      self.interface.createrepo()      
      createrepo = False

    pkgs = self.getRepoContents('localrepo')
    if self.compareRepoContents('localrepo', pkgs):
      if createrepo:
        self.interface.createrepo()        
      # HACK ALERT: need to the remove the .depsolve/localrepo folder so
      # that depsolver picks up the new RPM.      
      rm(join(self.interface.METADATA_DIR, '.depsolve/localrepo'),
         recursive=True, force=True)
      
      self.interface.cvars['input-store-changed'] = True

    if not self.interface.cvars['input-store-lists']:
      self.interface.cvars['input-store-lists'] = {}
    self.interface.cvars['input-store-lists'].update({'localrepo': pkgs})

class LocalRepogenHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.__init__.repogen'
    self.interface = interface

  def post(self):
    if not self.interface.cvars['repoconfig-file']: return
    lines = filereader.read(self.interface.cvars['repoconfig-file'])
    lines.append('[localrepo]')
    lines.append('name = localrepo')
    lines.append('baseurl = file://%s' % join(self.interface.METADATA_DIR, 'localrepo/'))
    filereader.write(lines, self.interface.cvars['repoconfig-file'])
