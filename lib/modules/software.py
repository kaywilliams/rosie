import re
import rpm
import os

from os.path       import join
from rpmUtils.arch import getArchList

import dims.osutils as osutils
import dims.mkrpm   as mkrpm
import dims.shlib   as shlib
import dims.sortlib as sortlib
import dims.spider  as spider
import dims.sync    as sync

from callback  import BuildSyncCallback
from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface, VersionMixin, ListCompareMixin
from main      import BOOLEANS_TRUE

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'software',
    'interface': 'SoftwareInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['software'],
    'requires': ['comps.xml', 'pkglist', 'RPMS'],
  },
]

RPM_PNVRA_REGEX = re.compile('(.*/)?(.+)-(.+)-(.+)\.(.+)\.[Rr][Pp][Mm]')
RPM_GLOB = '*.[Rr][Pp][Mm]'

class SoftwareInterface(EventInterface, VersionMixin, ListCompareMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    VersionMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()))
    ListCompareMixin.__init__(self)
    
    self.product = self._base.base_vars['product']
    self.ts = rpm.TransactionSet()
    self.callback = BuildSyncCallback(base.log.threshold)
    
    self.rpmdest = join(self.getSoftwareStore(), self.product, 'RPMS')
    
  def rpmNameDeformat(self, rpm):
    """ 
    p[ath],n[ame],v[ersion],r[elease],a[rch] = SoftwareInterface.rpmNameDeformat(rpm)
    
    Takes an rpm with an optional path prefix and splits it into its component parts.
    Returns a path, name, version, release, arch tuple.
    """
    try:
      return RPM_PNVRA_REGEX.match(rpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, "DEBUG: Unable to extract rpm information from name '%s'" % rpm)
      return (None, None, None, None, None)
  
  def nvr(self, rpm):
    "nvr = SoftwareInterface.nvr(rpm) - convert an RPM filename into an NVR string"
    _,n,v,r,_ = self.rpmNameDeformat(rpm)
    return '%s-%s-%s' % (n,v,r)
  
  def rpmCheckSignature(self, rpm, pubkey, verbose=True):
    "Check RPM signature's validity.  Raises mkrpm.rpmsign.SignatureInvalidException"
    if verbose: self._base.log.write(2, osutils.basename(rpm), 40)
    if len(pubkey) == 0: raise RuntimeError, "No GPG keys found to check against"
    mkrpm.rpmsign.verifyRpm(rpm, public=pubkey, force=True)
  
  def syncRpm(self, rpm, store, path):
    "Sync an rpm from path within store into the the output store"
    #self.log(1, "   - downloading %s" % rpm)
    path = self.cache(join(path, rpm), prefix=store, callback=self.callback)
    rpmsrc  = join(self.getInputStore(), store, path)
    sync.sync(rpmsrc, self.rpmdest)
  
  def deleteRpm(self, rpm):
    "Delete an rpm from the output store"
    self.log(2, "deleting %s" % rpm)
    osutils.rm(join(self.rpmdest, '%s.*.[Rr][Pp][Mm]' % rpm))
  
  def signRpm(self, rpm, pubkey, seckey, password):
    "Sign an RPM"
    self.log(2, "signing %s" % osutils.basename(rpm))
    for r in osutils.find(self.rpmdest, name='%s.*.[Rr][Pp][Mm]' % rpm, maxdepth=1):
      mkrpm.rpmsign.signRpm(r, public=pubkey, secret=seckey, passphrase=password)
  
  def createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.getSoftwareStore())
    self.log(2, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q -g %s/base/comps.xml .' % self.product)
    os.chdir(pwd)
  
  def genhdlist(self):
    "Run genhdlist on the output store.  Only necesary in some versions of anaconda"
    self.log(2, "running genhdlist")
    shlib.execute('/usr/lib/anaconda-runtime/genhdlist --productpath %s %s' % \
                  (self.product, self.getSoftwareStore()))

def presoftware_hook(interface):
  if interface.eventForceStatus('software'):
    osutils.rm(interface.rpmdest, recursive=True, force=True)

def software_hook(interface):
  "Build a software store"
  # the --force option may not perform exactly as desired for this
  # TODO discuss and examine possibilities
  interface.log(0, "processing rpms")
  osutils.mkdir(interface.rpmdest, parent=True)

  handler = SoftwareHandler(interface)
  handler.handle()
  

class SoftwareHandler:
  def __init__(self, interface):
    self.interface = interface
    self.interface.lfn = self.delete_rpm
    self.interface.rfn = self.download_rpm
    self.interface.cb = self
    
    self.changed = False
    self._packages = {}
    self._validarchs = getArchList(self.interface.arch)
    self._tocheck = []
    
  def handle(self):
    "Generate a software store"
    # construct a list of rpms without .<arch>.rpm
    rpmlist = []
    for rpm in osutils.find(self.interface.rpmdest, name=RPM_GLOB, prefix=False):
      nvr = self.interface.nvr(rpm)
      if nvr not in rpmlist: rpmlist.append(nvr)
    
    # call interface.lfn (delete_rpm()) and interface.rfn (download_rpm())
    # on each rpm in rpmlist not in the cvar, and each rpm in the cvar not
    # in rpmlist, respectively
    self.interface.compare(rpmlist, self.interface.get_cvar('pkglist'))
    self.check_rpm_signatures()
    self.create_metadata()
  
  # callback functions
  def notify_both(self, i): pass
  def notify_left(self, i):
    self.changed = True
    self.interface.log(1, "deleting old rpms (%d packages)" % i)
  def notify_right(self, i):
    self.changed = True
    self.interface.log(1, "downloading new rpms (%d packages)" % i)
    for store in self.interface.config.mget('//stores/*/store/@id'):
      i,s,n,d,u,p = self.interface.getStoreInfo(store)
      
      base = self.interface.storeInfoJoin(s,n,d)
      
      # get the list of .rpms in the input store
      for rpm in self.interface.get_cvar('input-store-lists')[store]:
        _,n,v,r,a = self.interface.rpmNameDeformat(rpm)
        nvr = '%s-%s-%s' % (n,v,r)
        if not self._packages.has_key(nvr):
          self._packages[nvr] = {}
        if not self._packages[nvr].has_key(a):
          self._packages[nvr][a] = []
        self._packages[nvr][a].append((i,d,rpm))
    
  def delete_rpm(self, rpm): # lfn
    self.interface.deleteRpm(rpm)
  
  def download_rpm(self, rpm): # rfn
    for arch in self._packages[rpm]:
      if arch in self._validarchs:
        try:
          store, path, rpmname = self._packages[rpm][arch][0]
          self.interface.syncRpm(rpmname, store, path)
          self._tocheck.append((osutils.basename(rpmname), store))
        except IndexError, e:
          self.errlog(1, "No rpm '%s' found in store '%s' for arch '%s'" % (rpm, store, arch))
    self.interface.set_cvar('new-rpms', self._tocheck) #!
  
  def check_rpm_signatures(self):
    if len(self._tocheck) == 0:
      return
    self.interface.log(1, "checking gpgkeys on new rpms")
    
    gpgkeys = self._prepare_gpgcheck()
    
    for rpm, store in self._tocheck:
      if self.interface.config.get(['//stores/*/store[@id="%s"]/gpgcheck/text()' % store,
                                    '//stores/gpgcheck/text()'],
                                   'False') not in BOOLEANS_TRUE:
        continue
      
      invalids = []
      try:
        self.interface.rpmCheckSignature(join(self.interface.rpmdest, rpm), gpgkeys)
        self.interface.log(None, "OK")
      except mkrpm.rpmsign.SignatureInvalidException:
        self.interface.log(None, "INVALID")
        invalids.append(osutils.basename(rpm))
      
      if invalids:
        raise RpmSignatureInvalidError, "One or more RPMS failed GPG key checking: %s" % invalids
    self._clean_gpgcheck()
  
  def _prepare_gpgcheck(self):
    gpgtemp = join(self.interface.getTemp(), 'gpgkeys')
    osutils.mkdir(gpgtemp)
    for store in self.interface.config.mget('//stores/*/store'):
      if store.iget('gpgcheck/text()', 'False') not in BOOLEANS_TRUE: continue
      key = store.iget('gpgkey/text()', None)
      if key: sync.sync(self.interface.config.expand(key), gpgtemp)
    return osutils.find(gpgtemp, maxdepth=1, type=osutils.TYPE_FILE)
  
  def _clean_gpgcheck(self):
    osutils.rm(join(self.interface.getTemp(), 'gpgkeys'), recursive=True, force=True)
  
  def create_metadata(self):
    # create repository metadata
    if self.changed:
      self.interface.log(1, "creating repository metadata")
      self.interface.createrepo()

      # run genhdlist, if anaconda version < 10.92
      if sortlib.dcompare(self.interface.anaconda_version, '10.92') < 0:
        self.interface.genhdlist()


class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
