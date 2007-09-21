import re

from dims import filereader
from dims import xmltree

from dims.dispatch import PROPERTY_META
from dims.shlib    import execute

from dimsbuild.event   import Event, RepoMixin
from dimsbuild.logging import L0, L1, L2
from dimsbuild.repo    import RepoFromXml

API_VERSION = 5.0

class ReposMetaEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'REPOS',
      properties = PROPERTY_META,
      provides = ['local-repodata'],
    )
    
    self.local_repodata = self.METADATA_DIR/'repos'
  
  def setup(self):
    self.local_repodata.mkdirs()
  
  def apply(self):
    self.cvars['local-repodata'] = self.local_repodata

class ReposEvent(Event, RepoMixin): #!
  def __init__(self):
    Event.__init__(self,
      id = 'repos',
      #provides = ['anaconda-version', 'repo-contents', 'local-repodata'],
      provides = ['repomd-files', 'repos'],
    )
    
    self.DATA = {
      'config':    ['/distro/repos/repo'],
      'input':     [], # filled later
      'output':    [], # filled later
    }
    
  def validate(self):
    self.validator.validate('/distro/repos', schemafile='repos.rng')
    if len(self.config.xpath('/distro/repos/repo[@type="base"]')) != 1:
      self.validator.raiseInvalidConfig("Config file must define one repo with type 'base'")
  
  def setup(self):
    self.setup_diff(self.DATA)
    
    self.repos = {}
    
    for repoxml in self.config.xpath('/distro/repos/repo'):
      # create repo object
      repo = RepoFromXml(repoxml)
      repo.local_path = self.cvars['local-repodata']/repo.id
      self.repos[repo.id] = repo
      
      # add repodata folder as input/output
      self.setup_sync(repo.ljoin(repo.repodata_path, 'repodata'),
                      paths=[repo.rjoin(repo.repodata_path, repo.mdfile)])
  
  def run(self):
    self.log(0, L0("processing input repositories"))
    
    # sync repodata folders to builddata
    self.sync_input()
    
    self.write_metadata()
    
  def apply(self):
    self.cvars['repomd-files'] = []
    
    for repo in self.repos.values():
      repomdfile = repo.ljoin(repo.repodata_path, repo.mdfile)
      if not repomdfile.exists():
        raise RuntimeError("Unable to find cached file at '%s'. Perhaps you "
        "are skipping the repomd event before it has been allowed to run "
        "once?" % repomdfile)
      
      self.cvars['repomd-files'].append(repomdfile)
      repomd = xmltree.read(repomdfile).xpath('//data')
      repo.readRepoData(repomd)
      
    self.cvars['repos'] = self.repos
    

class RepoContentsEvent(Event, RepoMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'repo-contents',
      provides = ['anaconda-version', 'repo-contents'],
      requires = ['repomd-files'],
    )
    
    self.DATA = {
      'variables': ['cvars[\'repomd-files\']'],
      'input':     [], # filled later
      'output':    [], # filled later
    }
    
  def setup(self):
    self.setup_diff(self.DATA)
    
    for repo in self.cvars['repos'].values():
      repo.pkgsfile = self.cvars['local-repodata']/repo.id/'packages'
      
      paths = []
      for fileid in repo.datafiles:
        paths.append(repo.rjoin(repo.repodata_path, 'repodata', repo.datafiles[fileid]))
      
      self.setup_sync(repo.ljoin(repo.repodata_path, 'repodata'), paths=paths)
  
  def run(self):
    self.sync_input()
    
    # process available package lists
    self.log(1, L1("reading available packages"))
    
    for repo in self.cvars['repos'].values():
    
      if self._diff_handlers['input'].diffdict.has_key( #!
        repo.rjoin(repo.repodata_path, 'repodata', repo.datafiles['primary'])):
        self.log(2, L2(repo.id))
        
        # read primary.xml file, store list of pkgs to a file
        repo.readRepoContents()
        repo.writeRepoContents(repo.pkgsfile)
        self.DATA['output'].append(repo.pkgsfile)
    
    self.write_metadata()
  
  def apply(self):
    for repo in self.cvars['repos'].values():
      if not repo.pkgsfile.exists():
        raise RuntimeError("Unable to find cached file at '%s'. Perhaps you "
        "are skipping the repo-contents event before it has been allowed to "
        "run once?" % repo.pkgsfile)
      
      repo.readRepoContents(repofile=repo.pkgsfile)

      # get anaconda_version, if base repo
      if repo.id == self.getBaseRepoId():
        self.cvars['anaconda-version'] = get_anaconda_version(repo.pkgsfile)


EVENTS = {'MAIN': [ReposMetaEvent], 'REPOS': [ReposEvent, RepoContentsEvent]}


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
