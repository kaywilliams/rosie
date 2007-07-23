from os.path import exists, join

from dims         import filereader
from dims.osutils import find, mkdir, rm

import dims.listcompare as listcompare

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_META, HookExit
from dimsbuild.interface import DiffMixin, Repo

from rpms.lib import RpmsInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'RPMS',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_META,
    'requires': ['repos'],
    'conditional-requires': ['rpm-source-files'],
  },
]

MODULES = [
  'config',
  'default_theme',
  'logos',  
  'release',
]

HOOK_MAPPING = {
  'RpmsHook'         : 'RPMS',
  'LocalRepogenHook' : 'repogen',
}

#--------- HOOKS ----------#
class RpmsHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 1
    self.ID = 'rpms.__init__.RPMS'
    self.interface = interface

    data = {
      'output': [self.interface.LOCAL_REPO],
    }

    DiffMixin.__init__(self, join(self.interface.METADATA_DIR, 'RPMS', 'RPMS.md'), data)

  def pre(self):
    self.interface.log(0, "generating custom rpms")
    
  def setup(self):
    if not exists(self.interface.LOCAL_REPO):
      mkdir(self.interface.LOCAL_REPO, parent=True)
    if not exists(join(self.interface.LOCAL_REPO, 'RPMS')):
      mkdir(join(self.interface.LOCAL_REPO, 'RPMS'), parent=True)
    if not exists(join(self.interface.LOCAL_REPO, 'SRPMS')):
      mkdir(join(self.interface.LOCAL_REPO, 'SRPMS'), parent=True)    
    
  def post(self):
    if self.interface.isSkipped('RPMS'): return
    self.interface.log(1, "checking repository metadata")
    if self.test_diffs():
      self.interface.log(2, "running createrepo")
      self.interface.createrepo(join(self.interface.LOCAL_REPO, 'RPMS'))
      self.interface.createrepo(join(self.interface.LOCAL_REPO, 'SRPMS'))

      # need to the remove the .depsolve/localrepo folder so that
      # depsolver picks up the new RPM.
      rm(join(self.interface.METADATA_DIR, '.depsolve/localrepo'),
         recursive=True, force=True)
      self.write_metadata()

    self._add_repo()
    self._add_source()

  def _add_repo(self):
    repo = Repo('localrepo')
    repo.local_path = join(self.interface.LOCAL_REPO, 'RPMS')
    repo.split(repo.local_path)

    repo.readRepoData()    
    repo.readRepoContents()
    repofile = join(self.interface.METADATA_DIR, 'localrepo.pkgs')
    
    if repo.compareRepoContents(repofile):      
      repo.changed = True
      self.interface.cvars['input-repos-changed'] = True
      repo.writeRepoContents(repofile)      
    
    if not self.interface.cvars['repos']:
      self.interface.cvars['repos'] = {}
    self.interface.cvars['repos'][repo.id] = repo

  def _add_source(self):
    if self.interface.cvars['source-include']:
      repo = Repo('localrepo-sources')
      repo.local_path = join(self.interface.LOCAL_REPO, 'SRPMS')
      repo.split(repo.local_path)

      repo.readRepoData()
      repo.readRepoContents()
      
      if not self.interface.cvars['source-repos']:
        self.interface.cvars['source-repos'] = {}
      self.interface.cvars['source-repos'][repo.id] = repo
        
class LocalRepogenHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.__init__.repogen'
    self.interface = interface

  def post(self):
    if not self.interface.cvars['repoconfig-file'] or self.interface.isSkipped('RPMS'): return
    lines = filereader.read(self.interface.cvars['repoconfig-file'])
    lines.append('[localrepo]')
    lines.append('name = localrepo')
    lines.append('baseurl = file://%s' % join(self.interface.METADATA_DIR, 'localrepo', 'RPMS'))
    filereader.write(lines, self.interface.cvars['repoconfig-file'])
