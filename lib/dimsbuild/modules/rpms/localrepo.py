import os

from dims import shlib

from dimsbuild.event   import Event
from dimsbuild.logging import L0, L1, L2
from dimsbuild.repo    import Repo

API_VERSION = 5.0

class LocalRepoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id='localrepo',
      comes_after=['logos-rpm', 'default-theme-rpm',
                  'release-rpm', 'config-rpm'],
      provides=['repos', 'source-repos', 'included-packages', 'excluded-packages'])

    self.LOCAL_RPMS  = self.mddir/'RPMS'
    self.LOCAL_SRPMS = self.mddir/'SRPMS'

    self.DATA = {
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.io.setup_sync(self.LOCAL_RPMS,  paths=self.cvars['custom-rpms'],  id='LOCAL_RPMS')
    self.io.setup_sync(self.LOCAL_SRPMS, paths=self.cvars['custom-srpms'], id='LOCAL_SRPMS')

    self.DATA['output'].append(self.LOCAL_RPMS/'repodata')
    self.DATA['output'].append(self.LOCAL_SRPMS/'repodata')    

  def run(self):
    self.log(0, L0("creating localrepo"))
    # remove previous output
    self.io.clean_eventcache(all=True)
    
    # sync rpms
    backup = self.files_callback.sync_start
    self.files_callback.sync_start = lambda: self.log(1, L1("copying custom rpms"))
    self.io.sync_input(copy=True, link=True, what='LOCAL_RPMS')
    self.files_callback.sync_start = lambda: self.log(1, L1("copying custom srpms"))
    self.io.sync_input(copy=True, link=True, what='LOCAL_SRPMS')
    self.files_callback.sync_start = backup
    
    self.log(1, L1("running createrepo"))
    self.log(2, L2(self.LOCAL_RPMS.basename))
    self._createrepo('localrepo', self.LOCAL_RPMS)
    self.log(2, L2(self.LOCAL_SRPMS.basename))
    self._createrepo('localrepo-sources', self.LOCAL_SRPMS)
    
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    self._populate()
    if self.cvars['custom-rpms']: self._add_store()
    if self.cvars['custom-srpms']: self._add_source()
  
  #----- HELPER METHODS -----#  
  def _createrepo(self, name, path):
    # createrepo
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(cwd)

    # create pkgsfile
    # TODO consider moving repo creation into setup function to eliminate 
    # duplicate code between _createrepo and _add_store functions
    repo = Repo(name)
    repo.local_path = path
    repo.remote_path = path
    repo.pkgsfile = path/'packages'
    repo.readRepoData()
    repo.readRepoContents()
    repo.writeRepoContents(repo.pkgsfile)
    self.DATA['output'].append(repo.pkgsfile)  
  
  def _add_store(self):
    repo = Repo('localrepo')
    repo.local_path = self.LOCAL_RPMS
    repo.remote_path = self.LOCAL_RPMS
    repo.pkgsfile = self.LOCAL_RPMS/'packages'
    repo.readRepoData()    
    repo.readRepoContents()
     
    if not self.cvars['repos']:
      self.cvars['repos'] = {}
    self.cvars['repos'][repo.id] = repo
  
  def _add_source(self):
    if self.cvars['sources-enabled']:
      repo = Repo('localrepo-sources')
      repo.local_path = self.LOCAL_SRPMS
      repo.remote_path = self.LOCAL_SRPMS
      
      repo.readRepoData()
      repo.readRepoContents()
      
      if not self.cvars['source-repos']:
        self.cvars['source-repos'] = {}
      self.cvars['source-repos'][repo.id] = repo
  
  def _populate(self):
    if not self.cvars.has_key('custom-rpms-info'): return
    
    for rpmname, type, requires, obsoletes in self.cvars['custom-rpms-info']:
      if not self.cvars['included-packages']:
        self.cvars['included-packages'] = []        
      self.cvars['included-packages'].append((rpmname, type, requires))
      
      if obsoletes:
        if not self.cvars['excluded-packages']:
          self.cvars['excluded-packages'] = []
        self.cvars['excluded-packages'].extend(obsoletes.split())


EVENTS = {'RPMS': [LocalRepoEvent]}
