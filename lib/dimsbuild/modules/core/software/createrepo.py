from dimsbuild.constants import RPM_REGEX
from dimsbuild.event     import Event
from dimsbuild.logging   import L0

from dimsbuild.modules.shared import CreateRepoMixin

API_VERSION = 5.0
EVENTS = {'software': ['CreaterepoEvent']}

class CreaterepoEvent(Event, CreateRepoMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'createrepo',
      provides = ['rpms', 'rpms-directory', 'repodata-directory'],
      requires = ['cached-rpms'],
      conditionally_requires = ['comps-file', 'signed-rpms', 'gpgsign-public-key'],
    )
    CreateRepoMixin.__init__(self)

    self.cvars['repodata-directory'] = self.SOFTWARE_STORE/'repodata'

    self.DATA = {
      'config':    ['.'],
      'variables': ['product'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.cvars['rpms-directory'] = self.SOFTWARE_STORE/self.product

    if self.cvars['comps-file']:
      self.DATA['input'].append(self.cvars['comps-file'])

    if self.cvars['gpgsign-public-key']: # if we're signing rpms #!
      paths = self.cvars['signed-rpms']
    else:
      paths = self.cvars['cached-rpms']

    self.io.setup_sync(self.cvars['rpms-directory'], paths=paths, id='rpms')

  def run(self):
    self.log(0, L0("creating repository metadata"))
    self.io.sync_input(link=True)

    # remove all obsolete RPMs
    old_files = set(self.cvars['rpms-directory'].findpaths(mindepth=1, regex=RPM_REGEX))
    new_files = set(self.io.list_output(what='rpms'))
    for obsolete_file in old_files.difference(new_files):
      obsolete_file.rm(recursive=True, force=True)

    # run createrepo
    repo_files = self.createrepo(self.SOFTWARE_STORE, groupfile=self.cvars['comps-file'])
    self.DATA['output'].extend(repo_files)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['rpms'] = self.io.list_output(what='rpms')
