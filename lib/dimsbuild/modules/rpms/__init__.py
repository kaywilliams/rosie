from os.path import exists, join

from dims         import filereader
from dims.osutils import find, mkdir, rm

import dims.listcompare as listcompare

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_META
from dimsbuild.interface import Repo

from rpms.lib import RpmsInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'RPMS',
    'provides': ['RPMS'],
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_META,
    'requires': ['repos'],
  },
]

MODULES = [
  'config',
  'default_theme',
  'logos',  
  'release',
]

SOURCE_XML = ''' 
<store id="localrepo-srpms">
  <path>file://%s</path>
</store>
'''

HOOK_MAPPING = {
  'LocalSrpmsHook'   : 'source',
  'RpmsHook'         : 'RPMS',
  'LocalRepogenHook' : 'repogen',
}

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
    repo = Repo('localrepo')
    repo.local_path = join(self.interface.METADATA_DIR, repo.id)
    repo.remote_path = 'file://%s' %repo.local_path
    repo.split('file:///%s' % repo.local_path)

    self.interface.createrepo()

    repo.readRepoData()    
    repo.readRepoContents()
    repofile = join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id)
    
    if repo.compareRepoContents(repofile):      
      repo.changed = True
      self.interface.cvars['input-repos-changed'] = True
      repo.writeRepoContents(repofile)      
      # HACK ALERT: need to the remove the .depsolve/localrepo folder so
      # that depsolver picks up the new RPM.      
      rm(join(self.interface.METADATA_DIR, '.depsolve/localrepo'),
         recursive=True, force=True)
    
    if not self.interface.cvars['repos']:
      self.interface.cvars['repos'] = {}
    self.interface.cvars['repos'][repo.id] = repo    

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
