import re

from os.path  import join, exists
from StringIO import StringIO

from dims import filereader
from dims import osutils
from dims import sync
from dims import xmltree

from dims.configlib import uElement

from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface, RepoFromXml, Repo

from dimsbuild.modules.lib import DiffMixin

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'repos',
    'provides': ['anaconda-version',
                 'repo-contents',
                 'input-repos-changed',
                 'local-repodata'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'EventInterface',
  },
]

HOOK_MAPPING = {
  'ReposHook':   'repos',
  'ValidateHook': 'validate',
}

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'repos.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/repos', schemafile='repos.rng')
    if len(self.interface.config.xpath('/distro/repos/repo[@type="base"]')) != 1:
      self.interface.raiseInvalidConfig("Config file must define one repo with type 'base'")
    

class ReposHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'repos.repos'
    
    self.interface = interface
    
    self.mdrepos = join(self.interface.METADATA_DIR, 'repos')
    
    self.DATA = {
      'config': ['/distro/repos/repo'],
      'input':  [], # to be filled later
      'output': [], # to be filled later
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'repos.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
    
  def force(self):
    for file in [ join(self.mdfile, repo.id) for repo in \
                  self.interface.getAllRepos() ]:
      osutils.rm(file, force=True)
    self.clean_metadata()
  
  def setup(self):
    self.interface.log(0, "generating filelists for input repositories")
    osutils.mkdir(self.mdrepos, parent=True)
    
    self.interface.cvars['repos'] = {}
    
    # sync all repodata folders to builddata
    self.interface.log(1, "synchronizing repository metadata")
    for repoxml in self.interface.config.xpath('/distro/repos/repo'):
      self.interface.log(2, repoxml.get('@id'))
      repo = RepoFromXml(repoxml)
      repo.local_path = join(self.mdrepos, repo.id)
      
      repo.getRepoData()
      
      self.interface.cvars['repos'][repo.id] = repo
      
      self.DATA['input'].append(join(self.mdrepos, repo.id, repo.repodata_path, 'repodata'))
      self.DATA['output'].append(join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id))
      
  def check(self):
    self.interface.cvars['input-repos-changed'] = self.interface.isForced('repos') or \
                                                  self.test_diffs()
    return self.interface.cvars['input-repos-changed']
  
  def run(self):
    self.interface.log(1, "computing repo contents")
    
    changed = False
    
    # generate repo RPM lists
    for repo in self.interface.getAllRepos():
      self.interface.log(2, repo.id)
      repo.readRepoContents()
      repofile = join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id)
      if repo.compareRepoContents(repofile):
        repo.changed = True; changed = True
        repo.writeRepoContents(repofile)
    
    self.interface.cvars['input-repos-changed'] = changed

  def apply(self):
    # populate the rpms list for each repo
    for repo in self.interface.getAllRepos():
      repofile = join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id)
      
      if not exists(repofile):
        raise RuntimeError, "Unable to find repo file '%s'" % repofile
      repo.rpms = filereader.read(repofile)
    
    # if we're skipping repos, assume repo lists didn't change; otherwise,
    # assume they did
    if self.interface.isSkipped('repos'):
      self.interface.cvars['input-repos-changed'] = False
    
    if not self.interface.cvars['anaconda-version']:
      anaconda_version = \
        get_anaconda_version(join(self.interface.METADATA_DIR,
                                  '%s.pkgs' % self.interface.getBaseRepoId()))
      self.interface.cvars['anaconda-version'] = anaconda_version
    
    self.interface.cvars['local-repodata'] = self.mdrepos

    self.write_metadata()
    

#------ HELPER FUNCTIONS ------#
def get_anaconda_version(file):
  scan = re.compile('.*anaconda-([\d\.]+-[\d\.]+)\..*\.[Rr][Pp][Mm]')
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
