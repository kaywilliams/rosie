import re

from dims import filereader

from dimsbuild.event    import Event
from dimsbuild.logging  import L0, L1, L2
from dimsbuild.validate import InvalidConfigError

from dimsbuild.modules.shared import RepoEventMixin

API_VERSION = 5.0

class ReposEvent(Event, RepoEventMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'repos',
      provides = ['anaconda-version',
                  'repos',         # provided by repos and localrepo events
                  'input-repos',   # provided by repos event only, used by release.py
                  'base-repoid'],
    )
    RepoEventMixin.__init__(self)

    self.DATA = {
      'config':    ['/distro/repos/repo'],
      'input':     [], # filled later
      'output':    [], # filled later
    }

  def validate(self):
    self.validator.validate('/distro/repos', schema_file='repos.rng')
    if len(self.config.xpath('/distro/repos/repo[@type="base"]')) != 1:
      raise InvalidConfig(self.config, "Config file must define one repo with type 'base'")

  def setup(self):
    self.diff.setup(self.DATA)
    self.cvars['base-repoid'] = self.config.get('/distro/repos/repo[@type="base"]/@id')
    self.read_config('/distro/repos/repo')

  def run(self):
    self.log(0, L0("setting up input repositories"))
    self.sync_repodata()

    # process available package lists
    self.log(1, L1("reading available packages"))
    self.read_new_packages()

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    for repo in self.repos.values():
      if not repo.pkgsfile.exists():
        raise RuntimeError("Unable to find cached file at '%s'. Perhaps you "
        "are skipping repos before it has been allowed to run once?" % repo.pkgsfile)

      repo.readRepoContents(repofile=repo.pkgsfile)

      # get anaconda_version, if base repo
      if repo.id == self.cvars['base-repoid']:
        self.cvars['anaconda-version'] = get_anaconda_version(repo.pkgsfile)

    self.cvars['repos'] = self.repos

EVENTS = {'SETUP': [ReposEvent]}


#------ HELPER FUNCTIONS ------#
def get_anaconda_version(file):
  scan = re.compile('(?:.*/)?anaconda-([\d\.]+-[\d\.]+)\..*\.[Rr][Pp][Mm]')
  version = None

  fl = filereader.read(file)
  for rpm in fl:
    match = scan.match(rpm)
    if match:
      try:
        version = match.groups()[0]
      except (AttributeError, IndexError), e:
        pass
      break
  if version is not None:
    return version
  else:
    raise ValueError, "unable to compute anaconda version from distro metadata"

#------ ERRORS ------#
class RepoNotFoundError(StandardError): pass
