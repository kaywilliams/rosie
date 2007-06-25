import re

from os.path  import join, exists
from StringIO import StringIO
from urlparse import urlparse

from dims import filereader
from dims import osutils
from dims import sync
from dims import xmltree

from dims.configlib import uElement

from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface, DiffMixin, RepoContentMixin

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
    parent = uElement('additional', self.config.get('//stores'))
    element = xmltree.read(StringIO(xml))
    parent.append(element)
    s,n,d,_,_,_ = urlparse(element.get('path/text()'))
    server = '://'.join((s,n))
  
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
  
  def pre(self):
    self.interface.log(0, "generating filelists for input stores")
    osutils.mkdir(self.mdstores, parent=True)
    
    # sync all repodata folders to builddata
    self.interface.log(1, "synchronizing repository metadata")
    for storeid in self.interface.getAllStoreIDs():
      info = self.interface.getStoreInfo(storeid)
      
      repodatapath = self.interface.config.get('//stores/*/store[@id="%s"]/repodata-path/text()' % storeid, '') #!
      
      self.interface.log(2, storeid)
      osutils.mkdir(join(self.mdstores, storeid, repodatapath, 'repodata'), parent=True)
      
      src = info.join(repodatapath)
      repomdfile = join(src, 'repodata/repomd.xml')
      dest = join(self.mdstores, storeid, 'repodata')
      sync.sync(repomdfile, dest, username=info.username, password=info.password)
      
      for file in xmltree.read(join(dest, 'repomd.xml')).xpath('//location/@href'):
        sync.sync(join(src, file), dest, username=info.username, password=info.password)
      
      self.DATA['input'].append(join(self.mdstores, storeid, 'repodata'))
      self.DATA['output'].append(join(self.interface.METADATA_DIR, '%s.pkgs' % storeid))
  
  def check(self):
    self.interface.cvars['input-store-changed'] = self.interface.isForced('stores') or \
                                                  self.test_diffs()
    return self.interface.cvars['input-store-changed']
  
  def run(self):
    self.interface.log(1, "computing store contents")
    
    storelists = {}
    changed = False
    
    # generate store lists
    for storeid in self.interface.getAllStoreIDs():
      self.interface.log(2, storeid)
      
      pkgs = self.getRepoContents(storeid)
      if self.compareRepoContents(storeid, pkgs):
        changed = True
      storelists[storeid] = pkgs
    
    self.interface.cvars['input-store-changed'] = changed
    self.interface.cvars['input-store-lists']   = storelists

  def apply(self):
    if not self.interface.cvars['input-store-lists']:
      storelists = {}
      
      for storeid in self.interface.getAllStoreIDs():
        storefile = join(self.interface.METADATA_DIR, '%s.pkgs' % storeid)
        if not exists(storefile):
          raise RuntimeError, "Unable to find store file '%s'" % storefile
        storelists[storeid] = filereader.read(storefile)
            
      self.interface.cvars['input-store-lists'] = storelists
    
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
