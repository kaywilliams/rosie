import re
import rpm
import os

from os.path       import join
from rpmUtils.arch import getArchList

from dims import osutils
from dims import mkrpm
from dims import shlib
from dims import sortlib
from dims import spider
from dims import sync

from callback  import BuildSyncCallback
from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface, ListCompareMixin
from main      import BOOLEANS_TRUE

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'software',
    'interface': 'SoftwareInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['rpms-directory', 'new-rpms'],
    'requires': ['pkglist', 'anaconda-version', 'input-store-lists'],
    'conditional-requires': ['comps-file', 'RPMS'],
  },
]

HOOK_MAPPING = {
  'SoftwareHook': 'software',
}


RPM_PNVRA_REGEX = re.compile('(.*/)?(.+)-(.+)-(.+)\.(.+)\.[Rr][Pp][Mm]')
RPM_GLOB = '*.[Rr][Pp][Mm]'


#------ INTERFACES ------#
class SoftwareInterface(EventInterface, ListCompareMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    ListCompareMixin.__init__(self)
    
    self.ts = rpm.TransactionSet()
    self.callback = BuildSyncCallback(base.log.threshold)
    
    self.rpmdest = join(self.SOFTWARE_STORE, self.product) 
    
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
    if verbose:
      self._base.log.write(2, osutils.basename(rpm), 40)
    if len(pubkey) == 0: 
      raise RuntimeError, "No GPG keys found to check against"
    mkrpm.rpmsign.verifyRpm(rpm, public=pubkey, force=True)
  
  def syncRpm(self, rpm, store, force=False):
    "Sync an rpm from path within store into the the output store"
    rpmsrc = self.cache(store, rpm, force=force, callback=self.callback)
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
    os.chdir(self.SOFTWARE_STORE)
    self.log(2, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q -g %s .' % join(self.METADATA_DIR, 'comps.xml'))
    os.chdir(pwd)
  
  def genhdlist(self):
    "Run genhdlist on the output store.  Only necesary in some versions of anaconda"
    self.log(2, "running genhdlist")
    shlib.execute('/usr/lib/anaconda-runtime/genhdlist --productpath %s %s' % \
                  (self.product, self.SOFTWARE_STORE))


#------ HOOKS ------#
class SoftwareHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'software.software'
    
    self.interface = interface
    
    # callback vars
    self.interface.lfn = self._delete_rpm
    self.interface.rfn = self._download_rpm
    self.interface.cb = self
    
    self._changed = False
    self._packages = {}
    self._validarchs = getArchList(self.interface.arch)
    self._new_rpms = []
  
  def force(self):
    osutils.rm(self.interface.rpmdest, recursive=True, force=True)
  
  def run(self):
    "Build a software store"
    self.interface.log(0, "processing rpms")
    osutils.mkdir(self.interface.rpmdest, parent=True)
  
    # construct a list of rpms without .<arch>.rpm
    rpmlist = []
    for rpm in osutils.find(self.interface.rpmdest, name=RPM_GLOB, prefix=False):
      nvr = self.interface.nvr(rpm)
      if nvr not in rpmlist: rpmlist.append(nvr)
    
    # call interface.lfn (_delete_rpm()) and interface.rfn (_download_rpm())
    # on each rpm in rpmlist not in the cvar, and each rpm in the cvar not
    # in rpmlist, respectively
    self.interface.compare(rpmlist, self.interface.cvars['pkglist'])
    self._check_rpm_signatures()
    self._create_metadata()
  
  def apply(self):
    osutils.mkdir(self.interface.rpmdest, parent=True)
    self.interface.cvars['new-rpms'] = self._new_rpms
    self.interface.cvars['rpms-directory'] = self.interface.rpmdest
  
  # callback functions
  def notify_both(self, i): pass
  def notify_left(self, i):
    self._changed = True
    self.interface.log(1, "deleting old rpms (%d packages)" % i)
  def notify_right(self, i):
    self._changed = True
    self.interface.log(1, "downloading new rpms (%d packages)" % i)
    for store in self.interface.config.xpath('//stores/*/store/@id'):
      # get the list of .rpms in the input store
      for rpm in self.interface.cvars['input-store-lists'][store]:
        _,n,v,r,a = self.interface.rpmNameDeformat(rpm)
        nvr = '%s-%s-%s' % (n,v,r)
        if not self._packages.has_key(nvr):
          self._packages[nvr] = {}
        if not self._packages[nvr].has_key(a):
          self._packages[nvr][a] = []
        self._packages[nvr][a].append((store,rpm))
    
  def _delete_rpm(self, rpm): # lfn
    self.interface.deleteRpm(rpm)
  
  def _download_rpm(self, rpm): # rfn
    for arch in self._packages[rpm]:
      if arch in self._validarchs:
        try:
          store, rpmname = self._packages[rpm][arch][0]
          self.interface.syncRpm(rpmname, store,
                                 force=self.interface.isForced('software'))
          self._new_rpms.append((osutils.basename(rpmname), store))
        except IndexError, e:
          self.errlog(1, "No rpm '%s' found in store '%s' for arch '%s'" % (rpm, store, arch))
  
  def _check_rpm_signatures(self):
    if len(self._new_rpms) == 0:
      return
    self.interface.log(1, "checking gpgkeys on new rpms")
    
    gpgkeys = self._prepare_gpgcheck()
    
    for rpm, store in self._new_rpms:
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
    gpgtemp = join(self.interface.TEMP_DIR, 'gpgkeys')
    osutils.mkdir(gpgtemp)
    for store in self.interface.config.xpath('//stores/*/store'):
      if store.get('gpgcheck/text()', 'False') not in BOOLEANS_TRUE: continue
      key = store.get('gpgkey/text()', None)
      if key: sync.sync(self.interface.config.expand(key), gpgtemp)
    return osutils.find(gpgtemp, maxdepth=1, type=osutils.TYPE_FILE)
  
  def _clean_gpgcheck(self):
    osutils.rm(join(self.interface.TEMP_DIR, 'gpgkeys'), recursive=True, force=True)
  
  def _create_metadata(self):
    # create repository metadata
    if self._changed:
      self.interface.log(1, "creating repository metadata")
      self.interface.createrepo()

      # run genhdlist, if anaconda version < 10.92
      if sortlib.dcompare(self.interface.cvars['anaconda-version'], '10.92') < 0:
        self.interface.genhdlist()


class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
