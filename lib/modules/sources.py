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

from callback  import BuildSyncCallback
from event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from interface import EventInterface, ListCompareMixin
from main      import BOOLEANS_TRUE, uElement

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'source',
    'provides': ['SRPMS'],
    'requires': ['software'],
    'conditional-requires': ['RPMS'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  },
]

HOOK_MAPPING = {
  'InitHook':     'init',
  'ApplyoptHook': 'applyopt',
  'SourceHook':   'source',
}


SRPM_PNVRA_REGEX = re.compile('(.*/)?(.+)-(.+)-(.+)\.(.+)\.[Ss][Rr][Cc]\.[Rr][Pp][Mm]')
SRPM_GLOB = '*.[Ss][Rr][Cc].[Rr][Pp][Mm]'
RPM_GLOB = '*.[Rr][Pp][Mm]'


class SrpmInterface(EventInterface, ListCompareMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    ListCompareMixin.__init__(self)
    self.ts = rpm.TransactionSet()
    self.callback = BuildSyncCallback(base.log.threshold)
    self.srpmdest = join(self.SOFTWARE_STORE, 'SRPMS')
  
  def srpmCheckSignatures(self, srpm, verbose=True):
    if verbose:
      self._base.log.write(2, "%s" % osutils.basename(srpm), 40)
    return #!
    # more stuff here
  
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
    store.parent = stores
    stores.append(store.root)
    s,n,d,_,_,_ = urlparse(store.iget('path/text()'))
    server = '://'.join((s,n))
    if server not in self._base.cachemanager.SOURCES:
      self._base.cachemanager.SOURCES.append(server)
  

#------ HOOKS ------#
class InitHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.init'
    
    self.interface = interface
  
  def run(self):
    parser = self.interface.getOptParser('build')
    
    parser.add_option('--no-srpms',
                      default=True,
                      dest='do_srpms',
                      action='store_false',
                      help='do not include SRPMS with the output distribution')


class ApplyoptHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.applyopt'
    
    self.interface = interface
  
  def run(self):
    self.interface.set_cvar('source-include', self.interface.options.do_srpms)


class SourceHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.source'
    
    self.interface = interface
    
    self.interface.lfn = self._delete_srpm
    self.interface.rfn = self._download_srpm
    self.interface.bfn = self._check_srpm
    self.interface.cb = self
    self._packages = {}

  def force(self):
    osutils.rm(self.interface.srpmdest, recursive=True, force=True)
    self.interface.set_cvar('source-include', True)
  
  def pre(self):
    self.interface.disableEvent('source')
    if self.interface.get_cvar('source-include') or \
       self.interface.config.get('//source/include/text()', 'False') in BOOLEANS_TRUE:
      if self.interface.get_cvar('pkglist-changed'):
        self.interface.enableEvent('source')
    else:
      self.flush()
  
  def run(self):
    "Generate SRPM store"
    self.interface.log(0, "processing srpms")
    self.interface.set_cvar('source-include', True)
    
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
  
  def _test_runstatus(self):
    if self.interface.get_cvar('source-include') or \
       self.interface.config.get('//source/include/text()', 'False') in BOOLEANS_TRUE:
      return self.interface.isForced('source') or \
             self.interface.get_cvar('pkglist-changed')
    else:
      return False
  
  # callback functions
  def notify_both(self, i):
    self.interface.log(1, "checking srpms (%d packages)" % i)
  def notify_left(self, i):
    self.interface.log(1, "deleting old srpms (%d packages)" % i)
  def notify_right(self, i):
    self.interface.log(1, "downloading new srpms (%d packages)" % i)
    # set up packages metadata dictionary for use in syncing
    for store in self.interface.config.mget('//source/stores/store/@id'):
      i,s,n,d,u,p = self.interface.getStoreInfo(store)
      
      base = self.interface.storeInfoJoin(s or 'file', n, d)
      srpms = spider.find(base, glob=SRPM_GLOB, prefix=False,
                          username=u, password=p)
      for srpm in srpms:
        _,n,v,r,a = self.interface.srpmNameDeformat(srpm)
        self._packages[srpm] = (i,d,srpm)

    osutils.mkdir(self.interface.srpmdest, parent=True)
    
  def _check_srpm(self, srpm):
    try:
      for path in osutils.expand_glob(join(self.interface.srpmdest, srpm)):
        self.interface.srpmCheckSignatures(path)
        if self.interface.logthresh >= 2:
          self.interface.log(None, "OK")
    except SrpmSignatureInvalidError:
      # remove invalid srpm and redownload
      self.interface.log(None, "INVALID: redownloading")
      osutils.rm(path, force=True)
      self.interface.r.append(srpm)
  
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
