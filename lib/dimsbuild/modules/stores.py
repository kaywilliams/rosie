import re

from os.path  import join, exists
from StringIO import StringIO
from urlparse import urlparse

from dims import filereader
from dims import osutils
from dims import sync
from dims import xmltree

from dims.configlib import uElement

from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface, DiffMixin, RepoContentMixin, RepoFromXml, Repo

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'stores',
    'provides': ['anaconda-version',
                 'input-store-lists',
                 'input-store-changed',
                 'local-repodata'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'StoresInterface',
  },
]

HOOK_MAPPING = {
  'StoresHook':   'stores',
  'ValidateHook': 'validate',
}

class StoresInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
  
  def add_store(self, xml):
    pass
    #parent = uElement('additional', self.config.get('//stores'))
    #element = xmltree.read(StringIO(xml))
    #parent.append(element)
    #s,n,d,_,_,_ = urlparse(element.get('path/text()'))
    #server = '://'.join((s,n))
  
  def getAllStoreIDs(self):
    return self.config.xpath('//stores/*/store/@id')


#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'stores.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('//stores', schemafile='stores.rng')
    

class StoresHook(DiffMixin, RepoContentMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'stores.stores'
    
    self.interface = interface
    
    self.mdstores = join(self.interface.METADATA_DIR, 'stores')
    
    self.DATA = {
      'config': ['//stores/*/store'],
      'input':  [], # to be filled later
      'output': [], # to be filled later
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'stores.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
    RepoContentMixin.__init__(self)
    
  def force(self):
    for file in [ join(self.mdfile, storeid) for storeid in \
                  self.interface.getAllStoreIDs() ]:
      osutils.rm(file, force=True)
  
  def setup(self):
    self.interface.log(0, "generating filelists for input stores")
    osutils.mkdir(self.mdstores, parent=True)
    
    self.interface.cvars['repos'] = {}
    
    # sync all repodata folders to builddata
    self.interface.log(1, "synchronizing repository metadata")
    for storeid in self.interface.config.xpath('//stores/*/store/@id'):
      self.interface.log(2, storeid)
      repo = RepoFromXml(self.interface.config.get('//stores/*/store[@id="%s"]' % storeid))
      repo.local_path = join(self.interface.METADATA_DIR, 'stores', repo.id)
      
      repo.getRepodata()
      
      self.interface.cvars['repos'][storeid] = repo
      
      self.DATA['input'].append(join(self.mdstores, storeid, 'repodata'))
      self.DATA['output'].append(join(self.interface.METADATA_DIR, '%s.pkgs' % storeid))
  
  def check(self):
    self.interface.cvars['input-store-changed'] = self.interface.isForced('stores') or \
                                                  self.test_diffs()
    return self.interface.cvars['input-store-changed']
  
  def run(self):
    self.interface.log(1, "computing store contents")
    
    changed = False
    
    # generate repo RPM lists
    for repo in self.interface.getAllRepos():
      self.interface.log(2, repo.id)
      pkgs = repo.getRepoContents()
      repofile = join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id)
      if repo.compareRepoContents(repofile):
        repo.changed = True; changed = True
        repo.writeRepoContents(repofile)
    
    self.interface.cvars['input-store-changed'] = changed

  def apply(self):
    # populate the rpms list for each repo
    for repo in self.interface.getAllRepos():
      repofile = join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id)
      
      if not exists(repofile):
        raise RuntimeError, "Unable to find store file '%s'" % repofile
      repo.rpms = filereader.read(repofile)
    
    # if we're skipping stores, assume store lists didn't change; otherwise,
    # assume they did
    if self.interface.isSkipped('stores'):
      self.interface.cvars['input-store-changed'] = False
    
    if not self.interface.cvars['anaconda-version']:
      anaconda_version = \
        get_anaconda_version(join(self.interface.METADATA_DIR,
                                  '%s.pkgs' % self.interface.getBaseStore()))
      self.interface.cvars['anaconda-version'] = anaconda_version
    
    self.interface.cvars['local-repodata'] = self.mdstores
    
    self.write_metadata()
    

#------ HELPER FUNCTIONS ------#
def get_anaconda_version(file):
  scan = re.compile('.*/anaconda-([\d\.]+-[\d\.]+)\..*\.[Rr][Pp][Mm]')
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
class StoreNotFoundError(StandardError): pass
