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
    
    self.mddir = join(self.interface.METADATA_DIR, 'repos')
    
    self.DATA = {
      'config': ['/distro/repos/repo'],
      'input':  [], # to be filled later
      'output': [], # to be filled later
    }
    self.mdfile = join(self.mddir, 'repos.md')
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)

    osutils.mkdir(self.mddir, parent=True)

    self.repos = {}
    self.interface.cvars['input-repos-changed'] = False

    for repoxml in self.interface.config.xpath('/distro/repos/repo'):
      # create repo objects
      repo = RepoFromXml(repoxml)
      repo.local_path = join(self.mddir, repo.id) 
      repo.pkgsfile = join(self.mddir, '%s.pkgs' % repo.id)

      # setup sync
      o = self.interface.setup_sync(paths=[(repo.rjoin(repo.repodata_path,'repodata'),
                                              repo.ljoin(repo.repodata_path))])

      # populate difftest variables
      self.DATA['output'].extend(o)
      self.DATA['output'].append(repo.pkgsfile)

      self.repos[repo.id] = repo

  def clean(self):
    self.interface.log(0, "cleaning repos event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "processing input repositories")

    # sync repodata folders to builddata
    self.interface.sync_input()

    self.interface.log(1, "reading available packages")    

    self.interface.repoinfo = {}

    for repo in self.repos.values():
      self.interface.log(2, repo.id)

      # read repomd.xml file
      repomd = xmltree.read(repo.ljoin(repo.repodata_path, repo.mdfile)).xpath('//data')
      repo.readRepoData(repomd)

      # read primary.xml file, store to a variable we can write into the repos.md file
      repo.readRepoContents()
      repo.writeRepoContents(repo.pkgsfile)

    if self.interface.has_changed('input'):
      self.interface.cvars['input-repos-changed'] = True

    self.interface.write_metadata()

  def apply(self):
    for repo in self.repos.values():
      # finish populating repo object, unless already done in run function
      if not self.interface.cvars['input-repos-changed']:
        repomdfile = repo.ljoin(repo.repodata_path, repo.mdfile)
        for file in repomdfile, repo.pkgsfile:
          if not exists(file):
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
