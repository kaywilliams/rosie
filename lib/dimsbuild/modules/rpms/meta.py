from os.path import exists, join

from dims import osutils

from dimsbuild.event     import EVENT_TYPE_META
from dimsbuild.interface import Repo

from lib import RpmsInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id':        'RPMS',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_META,
    'requires':  ['repos'],
    'conditional-requires': ['rpm-source-files'],
  },
]

HOOK_MAPPING = {
  'InitHook'    : 'init',     ## remove once testing is done
  'ApplyoptHook': 'applyopt', ## remove once testing is done
  'RpmsHook'    : 'RPMS',
}

#--------- HOOKS ----------#
class InitHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'meta.init'
    self.interface = interface

  def run(self):
    parser = self.interface.getOptParser()
    parser.add_option('--auto-bump',
                      default=False,
                      action='store_true',
                      metavar=' ',
                      dest='autobump',
                      help='increment the release number instead of prompting')
class ApplyoptHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'meta.applyopt'
    self.interface = interface

  def run(self):
    self.interface.cvars['auto-bump-release'] = self.interface.options.autobump
    
class RpmsHook:
  def __init__(self, interface):
    self.VERSION = 1
    self.ID = 'meta.RPMS'
    self.interface = interface
    
  def pre(self):
    self.interface.log(0, "generating custom rpms")
    
  def setup(self):
    osutils.mkdir(self.interface.LOCAL_REPO,  parent=True)
    osutils.mkdir(self.interface.LOCAL_RPMS,  parent=True)
    osutils.mkdir(self.interface.LOCAL_SRPMS, parent=True)
          
  def post(self):
    if self.interface.isSkipped('RPMS'): return
    self.interface.log(1, "checking repository metadata")

    if not exists(join(self.interface.LOCAL_RPMS, 'repodata')) or \
       not exists(join(self.interface.LOCAL_SRPMS, 'repodata')) or \
       self.interface.cvars['custom-rpms-built']:
      osutils.rm(join(self.interface.METADATA_DIR, '.depsolve', 'localrepo'),
                 recursive=True, force=True)
      self.interface.log(2, "running createrepo")
      self.interface.createrepo(self.interface.LOCAL_RPMS)
      self.interface.createrepo(self.interface.LOCAL_SRPMS)

    if self.interface.cvars['custom-rpms-info']:
      self.populate()
       
    self.add_store()
    self.add_source()

  #----- HELPER METHODS -----#
  def add_store(self):
    repo = Repo('localrepo')
    repo.local_path = self.interface.LOCAL_RPMS
    repo.remote_path = self.interface.LOCAL_RPMS
    repo.split(repo.local_path)

    repo.readRepoData()    
    repo.readRepoContents()
    repofile = join(self.interface.METADATA_DIR, 'localrepo.pkgs')
    
    if repo.compareRepoContents(repofile, what='file'):
      repo.changed = True
      self.interface.cvars['input-repos-changed'] = True
      repo.writeRepoContents(repofile)      
    
    if not self.interface.cvars['repos']:
      self.interface.cvars['repos'] = {}
    self.interface.cvars['repos'][repo.id] = repo

  def add_source(self):
    if self.interface.cvars['source-include']:
      repo = Repo('localrepo-sources')
      repo.local_path = self.interface.LOCAL_SRPMS
      repo.remote_path = self.interface.LOCAL_SRPMS
      repo.split(repo.local_path)

      repo.readRepoData()
      repo.readRepoContents()
      
      if not self.interface.cvars['source-repos']:
        self.interface.cvars['source-repos'] = {}
      self.interface.cvars['source-repos'][repo.id] = repo

  def populate(self):
    for rpmname, type, requires, obsoletes in self.interface.cvars['custom-rpms-info']:
      if not self.interface.cvars['included-packages']:
        self.interface.cvars['included-packages'] = []        
      self.interface.cvars['included-packages'].append((rpmname, type, requires))

      if obsoletes:
        if not self.interface.cvars['excluded-packages']:
          self.interface.cvars['excluded-packages'] = []
        self.interface.cvars['excluded-packages'].extend(obsoletes.split())
