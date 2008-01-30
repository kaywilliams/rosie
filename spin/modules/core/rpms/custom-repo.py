import os

from rendition import shlib

from spin.event   import Event
from spin.logging import L1, L2
from spin.repo    import RepoContainer

API_VERSION = 5.0

EVENTS = {'rpms': ['CustomRepoEvent']}

class CustomRepoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'custom-repo',
      conditionally_requires = ['custom-rpms-data'],
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

    if self.cvars['custom-rpms-data']:
      for id in self.cvars['custom-rpms-data'].keys():
        self.io.add_fpath(self.cvars['custom-rpms-data'][id]['rpm-path'],
                          self.CUSTOM_RPMS, id='custom-rpms')
        self.io.add_fpath(self.cvars['custom-rpms-data'][id]['srpm-path'],
                          self.CUSTOM_SRPMS, id='custom-rpms')

      self.rc.add_repo(self.cid, name=self.cid, baseurl=self.CUSTOM_RPMS)
      self.rc[self.cid].localurl = self.CUSTOM_RPMS
      self.rc[self.cid].pkgsfile = self.CUSTOM_RPMS/'packages'

      self.rc.add_repo(self.csid, name=self.csid, baseurl=self.CUSTOM_SRPMS)
      self.rc[self.csid].localurl = self.CUSTOM_SRPMS
      self.rc[self.csid].pkgsfile = self.CUSTOM_SRPMS/'packages'

      self.DATA['output'].append(self.CUSTOM_RPMS/'repodata')
      self.DATA['output'].append(self.CUSTOM_SRPMS/'repodata')
      try:
        self.rc[self.cid].update_metadata()
      except:
        pass
      try:
        self.rc[self.csid].update_metadata()
      except:
        pass
      self.DATA['output'].append(self.rc[self.cid].pkgsfile)
      self.DATA['output'].append(self.rc[self.csid].pkgsfile)

  def run(self):
    # remove previous output
    self.io.clean_eventcache(all=True)

    # sync rpms
    self.log(1, L1("copying packages"))
    if self.cvars['custom-rpms-data']:
      self.io.sync_input(link=True, what='custom-rpms',
                         text=self.log(4, L2("RPMS")))
      self.io.sync_input(link=True, what='custom-srpms',
                         text=self.log(4, L2("SRPMS")))

    self.log(1, L1("running createrepo"))
    if self.cvars['custom-rpms-data']:
      self.log(4, L2("RPMS"))
      self._createrepo(self.CUSTOM_RPMS)
      self.rc[self.cid].update_metadata()
      self.rc[self.cid].write_repo_content(self.rc[self.cid].pkgsfile)

      self.log(4, L2("SRPMS"))
      self._createrepo(self.CUSTOM_SRPMS)
      self.rc[self.csid].update_metadata()
      self.rc[self.csid].write_repo_content(self.rc[self.csid].pkgsfile)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self._populate()
    if self.cvars['custom-rpms-data']:
      try: # hack
        self.rc[self.cid].update_metadata()
      except:
        pass
      self.cvars['repos'][self.cid] = self.rc[self.cid]

      if self.cvars['source-repos']:
        try: # hack
          self.rc[self.csid].update_metadata()
        except:
          pass
        self.cvars['source-repos'][self.csid] = self.rc[self.csid]

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
    if not self.cvars.has_key('custom-rpms-data'): return

    for id in self.cvars['custom-rpms-data'].keys():
      default   = self.cvars['custom-rpms-data'][id]['packagereq-default']
      requires  = self.cvars['custom-rpms-data'][id]['packagereq-requires']
      type      = self.cvars['custom-rpms-data'][id]['packagereq-type']
      rpm_name  = self.cvars['custom-rpms-data'][id]['rpm-name']
      obsoletes = self.cvars['custom-rpms-data'][id]['rpm-obsoletes']
      (self.cvars.setdefault('included-packages', set())
         .add((rpm_name, type, requires, default)))
      if obsoletes:
        self.cvars.setdefault('excluded-packages', set()).update(obsoletes)
