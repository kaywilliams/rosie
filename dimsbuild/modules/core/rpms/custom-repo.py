import os

from dims import shlib

from dimsbuild.event   import Event
from dimsbuild.logging import L1, L2
from dimsbuild.repo    import RepoContainer

API_VERSION = 5.0

EVENTS = {'rpms': ['CustomRepoEvent']}

class CustomRepoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'custom-repo',
      conditionally_requires = ['custom-rpms', 'custom-srpms', 'custom-rpms-info'],
      provides = ['repos', 'source-repos', 'included-packages', 'excluded-packages']
    )
    self.rc = RepoContainer(self)

    self.CUSTOM_RPMS  = self.mddir/'RPMS'
    self.CUSTOM_SRPMS = self.mddir/'SRPMS'

    self.cid =  'custom-repo'
    self.csid = 'custom-repo-sources'

    self.DATA = {
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    if self.cvars['custom-rpms']:
      self.io.setup_sync(self.CUSTOM_RPMS,  paths=self.cvars['custom-rpms'],
                         id='CUSTOM_RPMS')

      self.DATA['output'].append(self.CUSTOM_RPMS/'repodata')

      self.rc.add_repo(self.cid, name=self.cid, baseurl=self.CUSTOM_RPMS)
      self.rc[self.cid].localurl = self.CUSTOM_RPMS
      self.rc[self.cid].pkgsfile = self.CUSTOM_RPMS/'packages'
      try:
        self.rc[self.cid].update_metadata()
      except:
        pass
      self.DATA['output'].append(self.rc[self.cid].pkgsfile)

    if self.cvars['custom-srpms']:
      self.io.setup_sync(self.CUSTOM_SRPMS, paths=self.cvars['custom-srpms'],
                         id='CUSTOM_SRPMS')

      self.DATA['output'].append(self.CUSTOM_SRPMS/'repodata')

      self.rc.add_repo(
        self.csid,
        name = self.csid,
        baseurl = self.CUSTOM_SRPMS
      )
      self.rc[self.csid].localurl = self.CUSTOM_SRPMS
      self.rc[self.csid].pkgsfile = self.CUSTOM_SRPMS/'packages'
      try:
        self.rc[self.csid].update_metadata()
      except:
        pass
      self.DATA['output'].append(self.rc[self.csid].pkgsfile)

  def run(self):
    # remove previous output
    self.io.clean_eventcache(all=True)

    # sync rpms
    self.log(1, L1("copying packages"))
    if self.cvars['custom-rpms']:
      self.io.sync_input(link=True, what='CUSTOM_RPMS',
                         text=self.log(4, L2("RPMS")))
    if self.cvars['custom-srpms']:
      self.io.sync_input(link=True, what='CUSTOM_SRPMS',
                         text=self.log(4, L2("SRPMS")))

    self.log(1, L1("running createrepo"))
    if self.cvars['custom-rpms']:
      self.log(4, L2("RPMS"))
      self._createrepo(self.CUSTOM_RPMS)
      self.rc[self.cid].update_metadata()
      self.rc[self.cid].write_repo_content(self.rc[self.cid].pkgsfile)
    if self.cvars['custom-srpms']:
      self.log(4, L2("SRPMS"))
      self._createrepo(self.CUSTOM_SRPMS)
      self.rc[self.csid].update_metadata()
      self.rc[self.csid].write_repo_content(self.rc[self.csid].pkgsfile)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self._populate()
    if self.cvars['custom-rpms']:
      try: # hack
        self.rc[self.cid].update_metadata()
      except:
        pass
      self.cvars['repos'][self.cid] = self.rc[self.cid]
    if self.cvars['custom-srpms'] and self.cvars['source-repos']:
      try: # hack
        self.rc[self.csid].update_metadata()
      except:
        pass
      self.cvars['source-repos'][self.csid] = \
        self.rc[self.csid]

  def verify_repodata(self):
    "repodata exists"
    if self.cvars['custom-rpms']:
      customrepo = self.rc[self.cid]
      self.verifier.failUnlessExists(customrepo.localurl / customrepo.mdfile)
      self.verifier.failUnlessExists(customrepo.localurl /
                                     'repodata' /
                                     customrepo.datafiles['primary'])
    if self.cvars['custom-srpms']:
      customrepo = self.rc[self.csid]
      self.verifier.failUnlessExists(customrepo.localurl / customrepo.mdfile)
      self.verifier.failUnlessExists(customrepo.localurl /
                                     'repodata' /
                                     customrepo.datafiles['primary'])

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
      (self.cvars.setdefault('included-packages', set())
         .add((rpmname, type, requires, default)))

      if obsoletes:
        self.cvars.setdefault('excluded-packages', set()).update(obsoletes)
