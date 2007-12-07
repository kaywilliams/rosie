import re

from dimsbuild.event    import Event
from dimsbuild.logging  import L1, L2
from dimsbuild.validate import InvalidConfigError

from dimsbuild.modules.shared import RepoEventMixin

API_VERSION = 5.0
EVENTS = {'setup': ['ReposEvent']}

class ReposEvent(Event, RepoEventMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'repos',
      provides = ['anaconda-version',
                  'logos-versions',
                  'release-versions',
                  'repos',         # provided by repos and localrepo events
                  'input-repos',   # provided by repos event only, used by release-rpm
                  'base-repoid',],
    )
    RepoEventMixin.__init__(self)

    self.DATA = {
      'variables': [], # filled later
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

  def validate(self):
    if self.config.get('base-repo/text()', None) is None:
      raise InvalidConfigError(self.config,
         "Config file must define a 'base-repo' element with the id "
         "of the base repo to use in dimsbuild processing")
    if self.config.get('repo', None) is None and \
       self.config.get('repofile', None) is None:
      raise InvalidConfigError(self.config,
         "Config file must specify at least one 'repo' element or "
         "at least one 'repofile' element as a child to the 'repos' "
         "element.")

  def setup(self):
    self.diff.setup(self.DATA)
    self.cvars['base-repoid'] = self.config.get('base-repo/text()')
    self.read_config(repos='repo', files='repofile')

  def run(self):
    self.sync_repodata()

    # process available package lists
    self.log(1, L1("reading available packages"))
    self.read_new_packages()

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    for repo in self.repocontainer.values():
      repo._read_repo_content(repofile=repo.pkgsfile)

      # get anaconda_version, if base repo
      if repo.id == self.cvars['base-repoid']:
        anaconda_version = get_package_version(['anaconda'], repo.pkgsfile)
        if anaconda_version is not None:
          name, version = anaconda_version
          self.cvars['anaconda-version'] = version
        else:
          raise ValueError("unable to compute anaconda version from distro metadata")

      # get logos and release versions, if any in repo
      pkgs = {'logos-versions': ['fedora-logos', 'centos-logos', 'redhat-logos'],
              'release-versions': ['fedora-release', 'centos-release', 'redhat-release',
                                   'fedora-release-notes', 'centos-release-notes',
                                   'redhat-release-notes']}

      for pkg in pkgs:
        pkg_version = get_package_version(pkgs[pkg], repo.pkgsfile)
        if pkg_version is not None:
          name, version = pkg_version
          self.cvars.setdefault(pkg, []).append((name, '==', version))

    self.cvars['repos'] = self.repocontainer
    
    if self.cvars['base-repoid'] not in self.repocontainer.keys():
      raise ValueError("Base repo id '%s' not found in any repo definition or "
                       "repo file given in config" % self.cvars['base-repoid'])

  def verify_pkgsfiles_exist(self):
    "verify all pkgsfiles exist"
    for repo in self.repocontainer.values():
      self.verifier.failUnless(repo.pkgsfile.exists(),
        "unable to find repo pkgsfile at '%s'" % repo.pkgsfile)


#------ HELPER FUNCTIONS ------#
def get_package_version(names, file):
  scan = re.compile('(?:.*/)?(' + "|".join(names) + ')-(.*)(\..*\..*$)')
  fl = file.read_lines()
  for rpm in fl:
    match = scan.match(rpm)
    if match:
      try:
        return match.groups()[0], match.groups()[1]
      except (AttributeError, IndexError), e:
        pass
  return None


#------ ERRORS ------#
class RepoNotFoundError(StandardError): pass

