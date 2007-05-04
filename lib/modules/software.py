import re
import rpm
import os

from os.path       import join
from rpmUtils.arch import getArchList

import dims.osutils     as osutils
import dims.shlib       as shlib
import dims.sortlib     as sortlib
import dims.spider      as spider
import dims.sync        as sync

from callback  import BuildSyncCallback
from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface, VersionMixin, ListCompareMixin

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'software',
    'interface': 'SoftwareInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['software'],
    'requires': ['comps.xml', 'pkglist', 'RPMS', 'IMAGES'],
  },
]

RPM_PNVRA_REGEX = re.compile('(.*/)?(.+)-(.+)-(.+)\.(.+)\.[Rr][Pp][Mm]')

class SoftwareInterface(EventInterface, VersionMixin, ListCompareMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    VersionMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()))
    ListCompareMixin.__init__(self)
    self.product = self._base.base_vars['product']
    self.ts = rpm.TransactionSet()
    self.callback = BuildSyncCallback(base.log.threshold)
    
    self.rpmdest = join(self.getSoftwareStore(), self.product, 'RPMS')
  
  def getPkglist(self):
    try:
      return self._base.pkglist
    except AttributeError:
      return None
  
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
  
  def rpmCheckSignatures(self, rpmpath, verbose=True):
    "Reads the rpm header to ensure the signature and gpg key validity of an rpm."
    if verbose:
      self._base.log.write(2, "%s" % osutils.basename(rpmpath), 40)
    return #!
    fd = os.open(rpmpath, os.O_RDONLY)
    try:
      try:
        self.ts.hdrFromFdno(fd)
      except rpm.error, e:
        raise RpmSignatureInvalidError, "Error reading rpm header for file %s: %s" % (rpmpath, str(e))
    finally:
      os.close(fd)
  
  def syncRpm(self, rpm, store, path):
    "Sync an rpm from path within store into the the output store"
    #self.log(1, "   - downloading %s" % rpm)
    path = self.cache(join(path, rpm), prefix=store, callback=self.callback)
    rpmsrc  = join(self.getInputStore(), store, path)
    sync.sync(rpmsrc, self.rpmdest)
    self.rpmCheckSignatures(join(self.rpmdest, osutils.basename(rpm)), verbose=False) # raises RpmSignatureInvalidError
  
  def deleteRpm(self, rpm):
    "Delete an rpm from the output store"
    self.log(2, "deleting %s" % rpm)
    osutils.rm(join(self.rpmdest, '%s.*.[Rr][Pp][Mm]' % rpm))

  def createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.getSoftwareStore())
    # run createrepo
    self.log(2, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q -g %s/base/comps.xml .' % self.product)
    os.chdir(pwd)
  
  def genhdlist(self):
    "Run genhdlist on the output store.  Only necesary in some versions of anaconda"
    self.log(2, "running genhdlist")
    shlib.execute('/usr/lib/anaconda-runtime/genhdlist --productpath %s %s' % \
                  (self.product, self.getSoftwareStore()))


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
    self.interface.bfn = self.check_rpm
    self.interface.cb = self
    
    self.changed = False
    self._packages = {}
    self._validarchs = getArchList(self.interface.arch)
    self._tosign = []
  
  def handle(self):
    "Generate a software store"
    rpms = osutils.find(self.interface.rpmdest, name='*.[Rr][Pp][Mm]', prefix=False)
  
    # construct a list of rpms without .<arch>.rpm
    rpmlist = []
    for rpm in rpms:
      _,name,version,release,_ = self.interface.rpmNameDeformat(rpm)
      fullname = '%s-%s-%s' % (name, version, release)
      if fullname not in rpmlist: rpmlist.append(fullname)
  
    self.interface.compare(rpmlist, self.interface.getPkglist())
    self.sign_rpms()
    self.create_metadata()
  
  # callback functions
  def notify_both(self, i):
    self.interface.log(1, "checking rpm signatures (%d packages)" % i)
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
      rpms = spider.find(base, glob='*.[Rr][Pp][Mm]', prefix=False,
                         username=u, password=p)
      for rpm in rpms:
        _,name,version,release,arch = self.interface.rpmNameDeformat(rpm)
        fullname = '%s-%s-%s' % (name, version, release)
        if not self._packages.has_key(fullname):
          self._packages[fullname] = {}
        if not self._packages[fullname].has_key(arch):
          self._packages[fullname][arch] = []
        self._packages[fullname][arch].append((i,d,rpm))
    
  def check_rpm(self, rpm):
    try:
      for path in osutils.expand_glob(join(self.interface.rpmdest, '*%s*.[Rr][Pp][Mm]' % rpm)):
        self.interface.rpmCheckSignatures(path)
        if self.interface.logthresh >= 2:
          self.interface.log(None, "OK")
    except RpmSignatureInvalidError:
      # remove invalid rpm and redownload
      self.interface.log(None, "INVALID: redownloading")
      osutils.rm(path, force=True)
      self.interface.r.append(rpm)
  
  def delete_rpm(self, rpm):
    self.interface.deleteRpm(rpm)
  
  def download_rpm(self, rpm):
    for arch in self._packages[rpm]:
      if arch in self._validarchs:
        try:
          store, path, rpmname = self._packages[rpm][arch][0]
          self.interface.syncRpm(rpmname, store, path)
          self._tosign.append(rpmname)
        except IndexError, e:
          self.errlog(1, "No rpm '%s' found in store '%s' for arch '%s'" % (rpm, store, arch))
  
  def sign_rpms(self):
    # sign new packages
    ##args = ['/bin/rpm', '--addsign']
    ##args.extend([join(rpmdir, osutils.basename(rpm)) for rpm in tosign])
    ##os.spawnv(os.P_WAIT, '/bin/rpm', args)
    self.interface.log(1, "signing new rpms")
    args = ''
    for rpm in self._tosign: args = args + ' ' + rpm
    shlib.execute('expect -c "spawn /bin/rpm --addsign %s; send timeout -1; ' + \
                             'stty -echo; expect \\"Enter pass phrase: \\"; ' + \
                             'send \\"\\n\\"; expect exp_continue"')

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
