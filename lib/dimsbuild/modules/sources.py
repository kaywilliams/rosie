""" 
sources.py

downloads srpms 
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '1.1'
__date__    = 'June 12th, 2007'

import os
import re
import rpm

from StringIO import StringIO
from os.path  import join, exists

from dims import osutils
from dims import spider
from dims import sync
from dims import xmltree

from dims.configlib import uElement

from dimsbuild.constants import BOOLEANS_TRUE, RPM_GLOB, SRPM_GLOB, SRPM_PNVRA
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.interface import EventInterface, RepoFromXml, Repo

from dimsbuild.modules.lib import DiffMixin, ListCompareMixin

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'source',
    'provides': ['SRPMS', 'source-include', 'source-repos'],
    'requires': ['software', 'new-rpms', 'rpms-directory'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  },
]

HOOK_MAPPING = {
  'SourceHook': 'source',
  'ValidateHook': 'validate',
}

SRPM_PNVRA_REGEX = re.compile(SRPM_PNVRA)


class SrpmInterface(EventInterface, ListCompareMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    ListCompareMixin.__init__(self)
    self.ts = rpm.TransactionSet()
    self.ts.setVSFlags(-1)
    
    self.srpmdest = join(self.OUTPUT_DIR, 'SRPMS')
    
    self.cvars['source-include'] = self.config.get('/distro/source', '') != '' and \
      self.config.get('/distro/source/@enabled', 'True') in BOOLEANS_TRUE
  
  def syncSrpm(self, srpm, repo):
    "Sync a srpm from path within repo into the output store"
    self.cache(repo.rjoin(srpm), self.srpmdest)
  
  def deleteSrpm(self, srpm):
    "Delete a srpm from the output store"
    self.log(2, "deleting %s" % srpm)
    osutils.rm(join(self.srpmdest, srpm))
  
  def srpmNameDeformat(self, srpm):
    try:
      return SRPM_PNVRA_REGEX.match(srpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, "DEBUG: Unable to extract srpm information from name '%s'" % srpm)
      return (None, None, None, None, None)
  
  def getAllSourceRepos(self):
    return self.cvars['source-repos'].values()


#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/source', 'sources.rng')
    
class SourceHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.source'
    
    self.interface = interface
    
    self.DATA =  {
      'config': ['/distro/source'],
      'input':  [], # to be filled later
      'output': [self.interface.srpmdest],
    }
    
    self.mdsrcrepos = join(self.interface.METADATA_DIR, 'source-repos')
    self.mdfile = join(self.interface.METADATA_DIR, 'source.md')
    self._packages = {}
    
    self.dosource = self.interface.cvars['source-include']
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
  
  def setup(self):
    if not self.dosource: return
    osutils.mkdir(self.mdsrcrepos, parent=True)
    
    if not self.interface.cvars['source-repos']:
      self.interface.cvars['source-repos'] = {}
    
    for repo in self.interface.config.xpath('/distro/source/repo'):
      repoid = repo.get('@id')
      repo = RepoFromXml(repo)
      repo.local_path = join(self.mdsrcrepos, repo.id)
      
      repo.getRepoData()
      repo.readRepoContents()
      
      self.interface.cvars['source-repos'][repo.id] = repo
      
      self.DATA['input'].append(join(self.mdsrcrepos, repo.id, repo.repodata_path, 'repodata'))
  
  def clean(self):
    osutils.rm(self.interface.srpmdest, recursive=True, force=True)
    ##osutils.rm(self.mdsrcrepos, recursive=True, force=True) # breaks stuff
    self.clean_metadata()
  
  def check(self):
    return self.interface.cvars['new-rpms'] is not None or \
           not exists(self.interface.srpmdest) or \
           self.test_diffs()
  
  def run(self):
    "Generate SRPM store"
    # if we're not enabled, clean up output and return immediately
    if not self.dosource:
      self.clean()
      return
    
    self.interface.log(0, "processing srpms")
    
    self.interface.lfn = self._delete_srpm
    self.interface.rfn = self._download_srpm
    self.interface.cb = self
    
    # generate list of srpms we already have
    oldsrpmlist = osutils.find(self.interface.srpmdest, name=SRPM_GLOB, printf='%P')
    
    # generate list of srpms to get
    srpmlist = []
    for pkg in osutils.find(join(self.interface.SOFTWARE_STORE,
                                 self.interface.product),
                            name=RPM_GLOB):
      i = os.open(pkg, os.O_RDONLY)
      h = self.interface.ts.hdrFromFdno(i)
      os.close(i)
      srpm = h[rpm.RPMTAG_SOURCERPM]
      if srpm not in srpmlist: srpmlist.append(srpm)
    
    self.interface.compare(oldsrpmlist, srpmlist)
    
    osutils.rm(self.mdfile, force=True)

    self.write_metadata()

  def apply(self):
    if self.dosource:
      self.interface.cvars['source-include'] = True
  
  # callback functions
  def notify_both(self, i):
    pass
  def notify_left(self, i):
    self.interface.log(1, "deleting old srpms (%d packages)" % i)
  def notify_right(self, i):
    self.interface.log(1, "downloading new srpms (%d packages)" % i)
    # set up packages metadata dictionary for use in syncing
    for repo in self.interface.getAllSourceRepos():
      for srpm in repo.rpms:
        self._packages[srpm] = repo
    
    osutils.mkdir(self.interface.srpmdest, parent=True)
  
  def _delete_srpm(self, srpm):
    self.interface.deleteSrpm(srpm)
  
  def _download_srpm(self, srpm):
    if self._packages.has_key(srpm):
      self.interface.syncSrpm(srpm, self._packages[srpm])
    else:
      raise SrpmNotFoundError("missing '%s' srpm" % srpm)
  
#------ ERRORS ------#
class SrpmNotFoundError(StandardError): pass
