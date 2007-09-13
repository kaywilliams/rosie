from dimsbuild.repo import Repo

from dimsbuild.modules.rpms.lib import RpmBuildEvent

API_VERSION = 5.0

class LocalRepoEvent(RpmBuildEvent):
  def __init__(self):
    RpmBuildEvent.__init__(self,
      id = 'localrepo',
      comes_after = ['logos-rpm', 'config-rpm', 'default-theme-rpm',
                     'release-rpm'],
    )
  
  def _clean(self): pass
  #  self.LOCAL_REPO.rm(recursive=True, force=True)
  
  def _run(self):
    ##if self.isSkipped('RPMS'): return
    if not (self.LOCAL_RPMS/'repodata').exists() or \
       not (self.LOCAL_SRPMS/'repodata').exists() or \
       self.cvars['custom-rpms-built']:
      self.log(1, "running createrepo")
      self.createrepo(self.LOCAL_RPMS)
      self.createrepo(self.LOCAL_SRPMS)
    
    if self.cvars['custom-rpms-info']:
      self.populate()
    
    self.add_store()
    self.add_source()
  
  #----- HELPER METHODS -----#
  def add_store(self):
    repo = Repo('localrepo')
    repo.local_path = self.LOCAL_RPMS
    repo.remote_path = self.LOCAL_RPMS
    
    repo.readRepoData()    
    repo.readRepoContents()
    repofile = self.METADATA_DIR/'localrepo.pkgs'
    
    if repo.compareRepoContents(repofile, what='file'):
      repo.changed = True
      self.cvars['input-repos-changed'] = True
      repo.writeRepoContents(repofile)      
    
    if not self.cvars['repos']:
      self.cvars['repos'] = {}
    self.cvars['repos'][repo.id] = repo
  
  def add_source(self):
    if self.cvars['sources-enabled']:
      repo = Repo('localrepo-sources')
      repo.local_path = self.LOCAL_SRPMS
      repo.remote_path = self.LOCAL_SRPMS
      
      repo.readRepoData()
      repo.readRepoContents()
      
      if not self.cvars['source-repos']:
        self.cvars['source-repos'] = {}
      self.cvars['source-repos'][repo.id] = repo
  
  def populate(self):
    for rpmname, type, requires, obsoletes in self.cvars['custom-rpms-info']:
      if not self.cvars['included-packages']:
        self.cvars['included-packages'] = []        
      self.cvars['included-packages'].append((rpmname, type, requires))
      
      if obsoletes:
        if not self.cvars['excluded-packages']:
          self.cvars['excluded-packages'] = []
        self.cvars['excluded-packages'].extend(obsoletes.split())


EVENTS = {'RPMS': [LocalRepoEvent]}
