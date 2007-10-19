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

    self.rc.add_repo('localrepo', name='localrepo', baseurl=self.LOCAL_RPMS)
    self.rc['localrepo'].localurl = self.LOCAL_RPMS
    self.rc['localrepo'].pkgsfile = self.LOCAL_RPMS/'packages'
    self.DATA['output'].append(self.rc['localrepo'].pkgsfile)

    self.rc.add_repo('localrepo-sources', name='localrepo-sources', baseurl=self.LOCAL_SRPMS)
    self.rc['localrepo-sources'].localurl = self.LOCAL_SRPMS
    self.rc['localrepo-sources'].pkgsfile = self.LOCAL_SRPMS/'packages'
    self.DATA['output'].append(self.rc['localrepo-sources'].pkgsfile)
    
    self.cvars.setdefault('repos', {})
    self.cvars.setdefault('source-repos', {})

  def run(self):
    self.log(0, L0("creating local repository for distribution-specific packages"))
    # remove previous output
    self.io.clean_eventcache(all=True)

    # sync rpms
    self.log(1, L1("copying packages"))
    backup = self.files_callback.sync_start
    self.files_callback.sync_start = lambda : self.log(4, L1("RPMS"))
    self.io.sync_input(link=True, what='LOCAL_RPMS')
    self.files_callback.sync_start = lambda : self.log(4, L1("SRPMS"))
    self.io.sync_input(link=True, what='LOCAL_SRPMS')
    self.files_callback.sync_start = backup

    self.log(1, L1("running createrepo"))
    if self.cvars['custom-rpms']:
      self.log(4, L2("RPMS"))
      self._createrepo(self.LOCAL_RPMS)
      self.rc['localrepo'].update_metadata()
      self.rc['localrepo'].write_repo_content(self.rc['localrepo'].pkgsfile)
    if self.cvars['custom-srpms']:
      self.log(4, L2("SRPMS"))
      self._createrepo(self.LOCAL_SRPMS)
      self.rc['localrepo-sources'].update_metadata()
      self.rc['localrepo-sources'].write_repo_content(self.rc['localrepo'].pkgsfile)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self._populate()
    if self.cvars['custom-rpms']:
      self.rc['localrepo'].update_metadata()
      self.cvars['repos']['localrepo'] = self.rc['localrepo']
    if self.cvars['custom-srpms'] and self.cvars['source-repos']:
      self.rc['localrepo-sources'].update_metadata()
      self.cvars['source-repos']['localrepo-sources'] = \
        self.rc['localrepo-sources']

  #----- HELPER METHODS -----#
  def _createrepo(self, path):
    # createrepo
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo --update -q .')
    os.chdir(cwd)

  def _populate(self):
    if not self.cvars.has_key('custom-rpms-info'): return

    for rpmname, type, requires, obsoletes, default in \
        self.cvars['custom-rpms-info']:
      self.cvars.setdefault('included-packages', []).append((rpmname,
                                                             type,
                                                             requires,
                                                             default))

      if obsoletes:
        self.cvars.setdefault('excluded-packages', []).extend(obsoletes.split())


EVENTS = {'rpms': [LocalRepoEvent]}
