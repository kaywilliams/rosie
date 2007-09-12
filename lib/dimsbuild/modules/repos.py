import re

from dims import filereader
from dims import xmltree

from dims.shlib          import execute
from dimsbuild.event     import EVENT_TYPE_META, EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import RepoFromXml

API_VERSION = 4.0

EVENTS = [
  { 'id':        'REPOS',
    'provides': ['local-repodata',
                 'anaconda-version',
                 'repo-contents',
                 'repos'],
    'properties': EVENT_TYPE_META,
  },
  { 'id':        'repomd',
    'parent':    'REPOS', 
    'provides':  'repomd-files',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
  {
    'id':        'repo-contents',
    'requires': ['repomd-files'],
    'provides': ['anaconda-version',
                 'repo-contents'],
    'parent':    'REPOS',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'ReposHook':         'REPOS',
  'RepomdHook':        'repomd',
  'RepoContentsHook':  'repo-contents',
  'ValidateHook':      'validate',
}

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 1
    self.ID = 'repos.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/repos', schemafile='repos.rng')
    if len(self.interface.config.xpath('/distro/repos/repo[@type="base"]')) != 1:
      self.interface.raiseInvalidConfig("Config file must define one repo with type 'base'")
    
class ReposHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'repos.REPO'

    self.interface = interface

  def apply(self):
    self.interface.cvars['local-repodata'] = self.interface.METADATA_DIR/'repos'

    if not self.interface.cvars['local-repodata'].exists(): 
      self.interface.cvars['local-repodata'].mkdirs()


class RepomdHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'repos.repomd'

    self.interface = interface

    self.DATA = {
      'config':    ['/distro/repos/repo'],
      'input':     [], # filled later
      'output':    [], # filled later
    }
    self.mdfile = self.interface.METADATA_DIR/'repomd.md'

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)

    self.repos = {}

    for repoxml in self.interface.config.xpath('/distro/repos/repo'):
      # create repo object
      repo = RepoFromXml(repoxml)
      repo.local_path = self.interface.cvars['local-repodata']/repo.id
      self.repos[repo.id] = repo

      # add repomd.xml as input/output
      self.interface.setup_sync(repo.ljoin(repo.repodata_path, 'repodata'),
                                paths=[repo.rjoin(repo.repodata_path,
                                                  repo.mdfile)])

  def clean(self):
    self.interface.log(0, "cleaning repomd event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "running repomd event")

    self.interface.sync_input()

    self.interface.write_metadata()

  def apply(self):

    self.interface.cvars['repomd-files'] = []
  
    for repo in self.repos.values():
      repomdfile = repo.ljoin(repo.repodata_path, repo.mdfile)
      if not repomdfile.exists():
        raise RuntimeError, "Unable to find cached file at '%s'. Perhaps you "\
        "are skipping the repos event before it has been allowed to run once?" \
        % repomdfile
   
      self.interface.cvars['repomd-files'].append(repomdfile)
      repomd = xmltree.read(repomdfile).xpath('//data')
      repo.readRepoData(repomd)

    self.interface.cvars['repos'] = self.repos
        
class RepoContentsHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'repos.repo-contents'
    
    self.interface = interface
    
    self.DATA = {
      'variables': ['cvars[\'repomd-files\']'], 
      'input':     [], # filled later
      'output':    [], # filled later
    }
    self.mdfile = self.interface.METADATA_DIR/'repo-contents.md'
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)

    for repo in self.interface.cvars['repos'].values():
      repo.pkgsfile = self.interface.cvars['local-repodata']/repo.id/'packages'

      paths = []
      for file in [ repo.groupfile, 
                    repo.primaryfile, 
                    repo.filelistsfile, 
                    repo.otherfile ]:
        if file: # some files may be missing, i.e. groupfile
          paths.append(repo.rjoin(repo.repodata_path, 'repodata', file))

      self.interface.setup_sync(repo.ljoin(repo.repodata_path, 'repodata'), 
                                paths=paths)

  def clean(self):
    self.interface.log(0, "cleaning repos event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "running repo-contents event")

    # sync repodata files builddata
    self.interface.sync_input()

    # process available package lists
    self.interface.log(1, "reading available packages")    

    self.interface.repoinfo = {}

    for repo in self.interface.cvars['repos'].values():
    
      if self.interface.handlers['input'].diffdict.has_key(
        repo.rjoin(repo.repodata_path,'repodata', repo.primaryfile)):
        self.interface.log(2, repo.id)

        # read primary.xml file, store list of pkgs to a file
        repo.readRepoContents()
        repo.writeRepoContents(repo.pkgsfile)
        self.DATA['output'].append(repo.pkgsfile)

    self.interface.write_metadata()

  def apply(self):
    for repo in self.interface.cvars['repos'].values():
      if not repo.pkgsfile.exists():
        raise RuntimeError, "Unable to find cached file at '%s'. Perhaps you "\
        "are skipping the repos event before it has been allowed to run once?" \
        % file
   
      repo.readRepoContents(repofile=repo.pkgsfile)

      # get anaconda_version, if base repo
      if repo.id == self.interface.getBaseRepoId():
        anaconda_version = get_anaconda_version(repo.pkgsfile)
        self.interface.cvars['anaconda-version'] = anaconda_version
  

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
