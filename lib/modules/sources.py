import os
import re
import rpm

from os.path            import join, exists
from urlgrabber.grabber import URLGrabError

import dims.osutils     as osutils
import dims.spider      as spider
import dims.sync        as sync

from callback  import BuildSyncCallback
from event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from interface import EventInterface, ListCompareMixin
from main      import BOOLEANS_TRUE

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'source',
    'provides': ['SRPMS'],
    'requires': ['RPMS', 'software'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  },
]

SRPM_PNVRA_REGEX = re.compile('(.*/)?(.+)-(.+)-(.+)\.(.+)\.[Ss][Rr][Cc]\.[Rr][Pp][Mm]')

class SrpmInterface(EventInterface, ListCompareMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    ListCompareMixin.__init__(self)
    self.ts = rpm.TransactionSet()
    self.callback = BuildSyncCallback(base.log.threshold)
    self.srpmdest = join(self.getSoftwareStore(), 'SRPMS')
  
  def srpmCheckSignatures(self, srpm, verbose=True):
    if verbose:
      self._base.log.write(2, "%s" % osutils.basename(srpm), 40)
    return #!
    # more stuff here
  
  def syncSrpm(self, srpm, store, path):
    "Sync a srpm from path within store into the output store"
    path = self.cache(join(path, srpm), prefix=store, callback=self.callback)
    srpmsrc  = join(self.getInputStore(), store, path)
    sync.sync(srpmsrc, self.srpmdest)
  
  def deleteSrpm(self, srpm):
    "Delete a srpm from the output store"
    self.log(2, "deleting %s" % srpm)
    osutils.rm(join(self.srpmdest, '%s.*.[Ss][Rr][Cc].[Rr][Pp][Mm]' % srpm))
  
  def srpmNameDeformat(self, srpm):
    try:
      return SRPM_PNVRA_REGEX.match(srpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, "DEBUG: Unable to extract srpm information from name '%s'" % srpm)
      return (None, None, None, None, None)


#------ HOOK FUNCTIONS ------#
def init_hook(interface):
  parser = interface.getOptParser('build')
  
  parser.add_option('--no-srpms',
                    default=True,
                    dest='do_srpms',
                    action='store_false',
                    help='do not include SRPMS with the output distribution')

def applyopt_hook(interface):
  interface.set_cvar('source-include', interface.options.do_srpms)

#def presource_hook(interface):
#  interface.disableEvent('source')
#  if interface.get_cvar('pkglist-changed'):
#    interface.enableEvent('source')

def source_hook(interface):
  if not interface.get_cvar('source-include') or \
     interface.config.get('//source/include/text()', 'False') not in BOOLEANS_TRUE:
    osutils.rm(interface.srpmdest, recursive=True, force=True)
    return
  
  interface.log(0, "processing srpms")
  interface.set_cvar('source-include', True)
  
  handler = SourcesHandler(interface)
  handler.handle()
  

class SourcesHandler:
  def __init__(self, interface):
    self.interface = interface
    self.interface.lfn = self.delete_srpm
    self.interface.rfn = self.download_srpm
    self.interface.bfn = self.check_srpm
    self.interface.cb = self
    self._packages = {}
  
  def handle(self):
    "Generate SRPM store"
    # generate list of srpms we already have
    oldsrpmlist = osutils.find(self.interface.srpmdest, name='*.[Ss][Rr][Cc].[Rr][Pp][Mm]',
                               prefix=False)
    
    # generate list of srpms to get
    srpmlist = []
    for pkg in osutils.find(join(self.interface.getSoftwareStore(),
                                 self.interface.product),
                            name='*.[Rr][Pp][Mm]', prefix=True):
      i = os.open(pkg, os.O_RDONLY)
      h = self.interface.ts.hdrFromFdno(i)
      os.close(i)
      srpm = h[rpm.RPMTAG_SOURCERPM]
      if srpm not in srpmlist: srpmlist.append(srpm)
    
    self.interface.compare(oldsrpmlist, srpmlist)
  
  # callback functions
  def notify_both(self, i):
    self.interface.log(1, "checking srpms (%d packages)" % i)
  def notify_left(self, i):
    self.interface.log(1, "deleting old srpms (%d packages)" % i)
  def notify_right(self, i):
    self.interface.log(1, "downloading new srpms (%d packages)" % i)
    # set up packages metadata dictionary for use in syncing
    for store in self.interface.config.mget('//source/*/store/@id'):
      i,s,n,d,u,p = self.interface.getStoreInfo(store)
      
      base = self.interface.storeInfoJoin(s or 'file', n, d)
      
      srpms = spider.find(base, glob='*[Ss][Rr][Cc].[Rr][Pp][Mm]', prefix=False,
                          username=u, password=p)
      
      for srpm in srpms:
        _,n,v,r,a = self.interface.srpmNameDeformat(srpm)
        self._packages[srpm] = (i,d,srpm)
    
    osutils.mkdir(self.interface.srpmdest, parent=True)
    
  def check_srpm(self, srpm):
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
  
  def delete_srpm(self, srpm):
    self.interface.deleteSrpm(srpm)
  
  def download_srpm(self, srpm):
    if self._packages.has_key(srpm):
      store, path, _ = self._packages[srpm]
      self.interface.syncSrpm(srpm, store, path)
  
  def compare(self, l1, l2):
    self.interface.compare(l1, l2)

class SourceStoreNotFoundError(StandardError): pass
class SrpmSignatureInvalidError(StandardError): pass
