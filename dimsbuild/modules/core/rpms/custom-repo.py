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

      id='custom-repo',
      conditionally_requires=['custom-rpms', 'custom-srpms', 'custom-rpms-info'],
      provides=['repos', 'source-repos', 'included-packages', 'excluded-packages']
    )
    self.rc = RepoContainer(self)

    self.CUSTOM_RPMS  = self.mddir/'RPMS'
    self.CUSTOM_SRPMS = self.mddir/'SRPMS'

    self.DATA = {
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.io.setup_sync(self.CUSTOM_RPMS,  paths=self.cvars['custom-rpms'],
                       id='CUSTOM_RPMS')
    self.io.setup_sync(self.CUSTOM_SRPMS, paths=self.cvars['custom-srpms'],
                       id='CUSTOM_SRPMS')

    self.DATA['output'].append(self.CUSTOM_RPMS/'repodata')
    self.DATA['output'].append(self.CUSTOM_SRPMS/'repodata')

    self.rc.add_repo('custom-repo', name='custom-repo', baseurl=self.CUSTOM_RPMS)
    self.rc['custom-repo'].localurl = self.CUSTOM_RPMS
    self.rc['custom-repo'].pkgsfile = self.CUSTOM_RPMS/'packages'
    self.DATA['output'].append(self.rc['custom-repo'].pkgsfile)

    self.rc.add_repo('custom-repo-sources', name='custom-repo-sources', baseurl=self.CUSTOM_SRPMS)
    self.rc['custom-repo-sources'].localurl = self.CUSTOM_SRPMS
    self.rc['custom-repo-sources'].pkgsfile = self.CUSTOM_SRPMS/'packages'
    self.DATA['output'].append(self.rc['custom-repo-sources'].pkgsfile)

    self.cvars.setdefault('repos', {})
    self.cvars.setdefault('source-repos', {})

  def run(self):
    # remove previous output
    self.io.clean_eventcache(all=True)

    # sync rpms
    self.log(1, L1("copying packages"))
    backup = self.files_callback.sync_start
    self.files_callback.sync_start = lambda : self.log(4, L1("RPMS"))
    self.io.sync_input(link=True, what='CUSTOM_RPMS')
    self.files_callback.sync_start = lambda : self.log(4, L1("SRPMS"))
    self.io.sync_input(link=True, what='CUSTOM_SRPMS')
    self.files_callback.sync_start = backup

    self.log(1, L1("running createrepo"))
    if self.cvars['custom-rpms']:
      self.log(4, L2("RPMS"))
      self._createrepo(self.CUSTOM_RPMS)
      self.rc['custom-repo'].update_metadata()
      self.rc['custom-repo'].write_repo_content(self.rc['custom-repo'].pkgsfile)
    if self.cvars['custom-srpms']:
      self.log(4, L2("SRPMS"))
      self._createrepo(self.CUSTOM_SRPMS)
      self.rc['custom-repo-sources'].update_metadata()
      self.rc['custom-repo-sources'].write_repo_content(self.rc['custom-repo'].pkgsfile)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self._populate()
    if self.cvars['custom-rpms']:
      self.rc['custom-repo'].update_metadata()
      self.cvars['repos']['custom-repo'] = self.rc['custom-repo']
    if self.cvars['custom-srpms'] and self.cvars['source-repos']:
      self.rc['custom-repo-sources'].update_metadata()
      self.cvars['source-repos']['custom-repo-sources'] = \
        self.rc['custom-repo-sources']

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
        self.cvars.setdefault('excluded-packages', []).extend(obsoletes)
