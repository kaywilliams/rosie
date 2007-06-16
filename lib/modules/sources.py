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
from urlparse import urlparse

from dims import osutils
from dims import spider
from dims import sync
from dims import xmltree

from dims.configlib import uElement

from callback  import BuildSyncCallback
from event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from interface import EventInterface, ListCompareMixin, DiffMixin
from main      import BOOLEANS_TRUE

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'source',
    'provides': ['SRPMS', 'source-include'],
    'requires': ['software', 'new-rpms', 'rpms-directory'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  },
]

HOOK_MAPPING = {
  'SourceHook': 'source',
  'ValidateHook': 'validate',
}


SRPM_PNVRA_REGEX = re.compile('(.*/)?(.+)-(.+)-(.+)\.([Ss][Rr][Cc])\.[Rr][Pp][Mm]')
SRPM_GLOB = '*.[Ss][Rr][Cc].[Rr][Pp][Mm]'
RPM_GLOB = '*.[Rr][Pp][Mm]'


class SrpmInterface(EventInterface, ListCompareMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    ListCompareMixin.__init__(self)
    self.ts = rpm.TransactionSet()
    self.ts.setVSFlags(-1)
    self.callback = BuildSyncCallback(base.log.threshold)
    self.srpmdest = join(self.DISTRO_DIR, 'SRPMS')
  
  def syncSrpm(self, srpm, store, path, force=False):
    "Sync a srpm from path within store into the output store"
    path = self.cache(join(path, srpm), prefix=store, callback=self.callback)
    ##uncomment the following when forced caching works
    ##path = self.cache(join(path, srpm), prefix=store, callback=self.callback, force=force)
    srpmsrc  = join(self.INPUT_STORE, store, path)
    sync.sync(srpmsrc, self.srpmdest)
  
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

  def add_store(self, storeXml):
    stores = uElement('stores', self.config.get('//source'))
    store = xmltree.read(StringIO(storeXml))
    stores.append(store)
    s,n,d,_,_,_ = urlparse(store.get('path/text()'))
    server = '://'.join((s,n))
    if server not in self._base.cachemanager.SOURCES:
      self._base.cachemanager.SOURCES.append(server)
  

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('//source', 'sources.rng')
    
class SourceHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.source'
    
    self.interface = interface

    self.DATA =  {
      'config': ['//source'],
      'output': [self.interface.srpmdest]
    }

    self.mdfile = join(self.interface.METADATA_DIR, 'source.md')

    DiffMixin.__init__(self, self.mdfile, self.DATA)

  def force(self):
    osutils.rm(self.interface.srpmdest, recursive=True, force=True)
    osutils.rm(self.mdfile, force=True)
  
  def check(self):
    if self.interface.config.get('//source/include/text()', 'False') in BOOLEANS_TRUE:
      return self.interface.cvars['new-rpms'] is not None or \
             not exists(self.interface.srpmdest) or \
             self.test_diffs()
    else:
      # clean up old output and metadata
      self.force()
      return False
   
  def run(self):
    "Generate SRPM store"
    self.interface.log(0, "processing srpms")

    self.interface.lfn = self._delete_srpm
    self.interface.rfn = self._download_srpm
    self.interface.cb = self
    self._packages = {}

    # generate list of srpms we already have
    oldsrpmlist = osutils.find(self.interface.srpmdest, name=SRPM_GLOB, prefix=False)
    
    # generate list of srpms to get
    srpmlist = []
    for pkg in osutils.find(join(self.interface.SOFTWARE_STORE,
                                 self.interface.product),
                            name=RPM_GLOB, prefix=True):
      i = os.open(pkg, os.O_RDONLY)
      h = self.interface.ts.hdrFromFdno(i)
      os.close(i)
      srpm = h[rpm.RPMTAG_SOURCERPM]
      if srpm not in srpmlist: srpmlist.append(srpm)

    self.interface.compare(oldsrpmlist, srpmlist)

    osutils.rm(self.mdfile, force=True)
    self.write_metadata()

  def apply(self):
    if self.interface.config.get('//source/include/text()', 'False') in BOOLEANS_TRUE:
      self.interface.cvars['source-include'] = True
  
  # callback functions
  def notify_both(self, i):
    pass
  def notify_left(self, i):
    self.interface.log(1, "deleting old srpms (%d packages)" % i)
  def notify_right(self, i):
    self.interface.log(1, "downloading new srpms (%d packages)" % i)
    # set up packages metadata dictionary for use in syncing
    for store in self.interface.config.xpath('//source/stores/store/@id'):
      i,s,n,d,u,p = self.interface.getStoreInfo(store)

      base = self.interface.storeInfoJoin(s or 'file', n, d)
      srpms = spider.find(base, glob=SRPM_GLOB, prefix=False,
                          username=u, password=p)
      for srpm in srpms:
        _,n,v,r,a = self.interface.srpmNameDeformat(srpm)
        self._packages[srpm] = (i,d,srpm)

    osutils.mkdir(self.interface.srpmdest, parent=True)
  
  def _delete_srpm(self, srpm):
    self.interface.deleteSrpm(srpm)
  
  def _download_srpm(self, srpm):
    if self._packages.has_key(srpm):
      store, path, _ = self._packages[srpm]
      self.interface.syncSrpm(srpm, store, path,
                              force=self.interface.isForced('source'))
    else:
      raise SrpmNotFoundError("missing '%s' srpm" %(srpm,))
  
#------ ERRORS ------#
class SrpmNotFoundError(StandardError): pass
class SourceStoreNotFoundError(StandardError): pass
class SrpmSignatureInvalidError(StandardError): pass
