import re

from dims import filereader
from dims import xmltree

from dims.shlib          import execute
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import RepoFromXml

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'repos',
    'provides': ['anaconda-version',
                 'repo-contents',
                 'repos-changed',
                 'local-repodata'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'ReposHook':   'repos',
  'ValidateHook': 'validate',
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
    self.ID = 'repos.repos'
    
    self.interface = interface
    
    self.mddir = self.interface.METADATA_DIR/'repos'
    
    self.DATA = {
      'config':    ['/distro/repos/repo'],
      'variables': [], # filled later
      'input':     [], # filled later
      'output':    [], # filled later
    }
    self.mdfile = self.mddir/'repos.md'
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)

    self.repos = {}
    self.interface.cvars['repos-changed'] = False
    self.gpgkeys = []  # list of gpgkey src,dest tuples
    self.primaryfiles = [] # list of primary xml files

    for repoxml in self.interface.config.xpath('/distro/repos/repo'):
      # create repo objects
      repo = RepoFromXml(repoxml)

      repo.local_path = self.mddir/repo.id
      repo.pkgsfile = self.mddir/repo.id/'packages'

      # add repodata folder as input/output
      self.DATA['output'].extend(
        self.interface.setup_sync(paths=[(repo.rjoin(repo.repodata_path,'repodata'),
                                          repo.ljoin(repo.repodata_path))]))

      # gpgkey related setup
      if repo.gpgcheck and not repo.gpgkeys:
        raise RuntimeError, \
              "Error: gpgcheck set but no gpgkeys provided for repo '%s'" % repo.id 

      if repo.gpgcheck and repo.gpgkeys:
        # add homedir var
        repo.homedir = repo.ljoin('homedir')

        # add gpgkeys as input/output
        for gpgkey in repo.gpgkeys:
          self.gpgkeys.append((gpgkey,repo.local_path))

      self.DATA['output'].extend(
        self.interface.setup_sync(paths=self.gpgkeys))

      self.repos[repo.id] = repo

    self.DATA['variables'].extend(['gpgkeys'])

  def clean(self):
    self.interface.log(0, "cleaning repos event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    if not self.mddir.exists(): self.mddir.mkdirs()

    if self.interface.has_changed('input'):
      self.interface.cvars['repos-changed'] = True

    self.interface.log(0, "processing input repositories")

    # sync repodata folders to builddata
    self.interface.sync_input()

    # process available package lists
    self.interface.log(1, "reading available packages")    

    self.interface.repoinfo = {}

    for repo in self.repos.values():
    
      # read repomd.xml file
      repomd = xmltree.read(repo.ljoin(repo.repodata_path, repo.mdfile)).xpath('//data')
      repo.readRepoData(repomd)

      if self.interface.handlers['input'].diffdict.has_key(
        repo.rjoin(repo.repodata_path,'repodata', repo.primaryfile)):
        self.interface.log(2, repo.id)

        # read primary.xml file, store list of pkgs to a file
        repo.readRepoContents()
        repo.writeRepoContents(repo.pkgsfile)
        self.DATA['output'].append(repo.pkgsfile)

    # process gpg keys
    if self.gpgkeys:

      # create gpg homedirs
      self.interface.log(1, "processing gpg keys") 
      for repo in self.repos.values():
        self.interface.log(2, repo.id)
        if repo.gpgcheck and repo.gpgkeys:
          for key in repo.gpgkeys:
            if not repo.homedir.exists(): repo.homedir.mkdirs()
            execute('gpg --homedir %s --import %s' %(repo.homedir, 
                                                     repo.ljoin(key.basename)))
          if repo.homedir:
            self.DATA['output'].append(repo.homedir)
        else:
          repo.ljoin('homedir').rm(force=True, recursive=True) 

    self.interface.write_metadata()

  def apply(self):
    for repo in self.repos.values():
      # finish populating repo object, unless already done in run function
      if not self.interface.cvars['repos-changed']:
        repomdfile = repo.ljoin(repo.repodata_path, repo.mdfile)
        for file in repomdfile, repo.pkgsfile:
          if not file.exists():
            raise RuntimeError, "Unable to find cached file at '%s'. Perhaps you are skipping the repos event before it has been allowed to run once?" % file
   
        repomd = xmltree.read(repo.ljoin(repo.repodata_path, repo.mdfile)).xpath('//data')
        repo.readRepoData(repomd)
        repo.readRepoContents(repofile=repo.pkgsfile)

      # get anaconda_version, if base repo
      if repo.id == self.interface.getBaseRepoId():
        anaconda_version = get_anaconda_version(repo.pkgsfile)
        self.interface.cvars['anaconda-version'] = anaconda_version

    self.interface.cvars['repos'] = self.repos
        
    self.interface.cvars['local-repodata'] = self.mddir
   

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
