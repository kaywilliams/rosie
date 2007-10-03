import os

from dims import shlib

from dimsbuild.event   import Event
from dimsbuild.logging import L0, L1, L2
from dimsbuild.repo    import RepoContainer

API_VERSION = 5.0

class LocalRepoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id='localrepo',
      conditionally_requires=['custom-rpms', 'custom-srpms', 'custom-rpms-info'],
      provides=['repos', 'source-repos', 'included-packages', 'excluded-packages']
    )
    self.rc = RepoContainer()
    
    self.LOCAL_RPMS  = self.mddir/'RPMS'
    self.LOCAL_SRPMS = self.mddir/'SRPMS'
        
    self.DATA = {
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.io.setup_sync(self.LOCAL_RPMS,  paths=self.cvars['custom-rpms'],
                       id='LOCAL_RPMS')
    self.io.setup_sync(self.LOCAL_SRPMS, paths=self.cvars['custom-srpms'],
                       id='LOCAL_SRPMS')

    self.DATA['output'].append(self.LOCAL_RPMS/'repodata')
    self.DATA['output'].append(self.LOCAL_SRPMS/'repodata')

    self.rc.add_repo('localrepo',
                     local_path=self.LOCAL_RPMS,
                     remote_path=self.LOCAL_RPMS)
    self.DATA['output'].append(self.rc.repos['localrepo'].pkgsfile)

    self.rc.add_repo('localrepo-sources',
                     local_path=self.LOCAL_SRPMS,
                     remote_path=self.LOCAL_SRPMS)
    self.DATA['output'].append(self.rc.repos['localrepo-sources'].pkgsfile)

  def run(self):
    self.log(0, L0("creating local repository for custom RPMs"))
    # remove previous output
    self.io.clean_eventcache(all=True)
    
    # sync rpms
    backup = self.files_callback.sync_start
    self.files_callback.sync_start = lambda : self.log(1, L1("copying custom rpms"))
    self.io.sync_input(copy=True, link=True, what='LOCAL_RPMS')
    self.files_callback.sync_start = lambda : self.log(1, L1("copying custom srpms"))
    self.io.sync_input(copy=True, link=True, what='LOCAL_SRPMS')
    self.files_callback.sync_start = backup
    
    self.log(1, L1("running createrepo"))
    
    self.log(2, L2("RPMS"))
    self._createrepo(self.LOCAL_RPMS)
    
    self.log(2, L2("SRPMS"))
    self._createrepo(self.LOCAL_SRPMS)

    self.rc.read_packages()
    
    self.diff.write_metadata()
    
  def apply(self):
    self.io.clean_eventcache()
    self._populate()
    if self.cvars['custom-rpms']:
      self.rc.read_packages(id='localrepo', write=False)
      if not self.cvars['repos']: self.cvars['repos'] = {}
      self.cvars['repos']['localrepo'] = self.rc.repos['localrepo']
    if self.cvars['custom-srpms'] and self.cvars['source-repos']:
      self.rc.read_packages(id='localrepo-sources', write=False)
      if not self.cvars['source-repos']: self.cvars['source-repos'] = {}
      self.cvars['source-repos']['localrepo-sources'] = self.rc.repos['localrepo-sources']
  
  #----- HELPER METHODS -----#
  def _createrepo(self, path):
    # createrepo
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo --update -q .')
    os.chdir(cwd)
  
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
