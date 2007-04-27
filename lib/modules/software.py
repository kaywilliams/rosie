import re
import rpm
import os

from os.path       import join
from rpmUtils.arch import getBaseArch

import dims.listcompare as listcompare
import dims.osutils     as osutils
import dims.shlib       as shlib
import dims.sortlib     as sortlib
import dims.spider      as spider
import dims.sync        as sync

from callback  import BuildSyncCallback
from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface, VersionMixin

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'software',
    'interface': 'SoftwareInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['software'],
    ##'requires': ['comps.xml', 'pkglist', 'RPMS', 'IMAGES'],
    'requires': ['comps.xml', 'pkglist'],
  },
]

RPM_PNVRA_REGEX = re.compile('(.*/)?(.+)-(.+)-(.+)\.(.+)\.[Rr][Pp][Mm]')

class SoftwareInterface(EventInterface, VersionMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    VersionMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()))
    self.product = self._base.base_vars['product']
    self.ts = rpm.TransactionSet()
    self.callback = BuildSyncCallback(base.log.threshold)
  
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
    path = self._base.cachemanager.get(join(path, rpm), prefix=store, callback=self.callback)
    rpmsrc  = join(self.getInputStore(), store, path)
    rpmdest = join(self.getSoftwareStore(), self.product, 'RPMS')
    sync.sync(rpmsrc, rpmdest)
    self.rpmCheckSignatures(join(rpmdest, osutils.basename(rpm)), verbose=False) # raises RpmSignatureInvalidError
  
  def deleteRpm(self, rpm):
    "Delete an rpm from the output store"
    self.log(2, "deleting %s" % rpm)
    osutils.rm(join(self.getSoftwareStore(), self.product, 'RPMS/%s.*.[Rr][Pp][Mm]' % rpm))

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
  rpmdir = join(interface.getSoftwareStore(), interface.product, 'RPMS')
  osutils.mkdir(rpmdir, parent=True)
  
  rpms = osutils.find(rpmdir, name='*.[Rr][Pp][Mm]', prefix=False)
  
  # construct a list of rpms without .<arch>.rpm
  rpmlist = []
  for rpm in rpms:
    _,name,version,release,_ = interface.rpmNameDeformat(rpm)
    fullname = '%s-%s-%s' % (name, version, release)
    if fullname not in rpmlist: rpmlist.append(fullname)
  
  old, new, both = listcompare.compare(rpmlist, interface.getPkglist())
  
  # check signatures on stuff in both lists
  if len(both) > 0:
    interface.log(1, "checking rpm signatures")
    for rpm in both:
      try:
        path = osutils.expand_glob(join(rpmdir, '*%s*.[Rr][Pp][Mm]' % rpm))[0]
        interface.rpmCheckSignatures(path)
        if interface.logthresh >= 2:
          interface.log(None, "OK")
      except IndexError:
        raise OSError, "RPM '%s' not found in input store" % rpm
      except RpmSignatureInvalidError:
        # remove invalid rpm and redownload
        interface.log(None, "INVALID: redownloading")
        osutils.rm(path, force=True)
        new.append(rpm)
  
  # delete old packages
  if len(old) > 0:
    interface.log(1, "deleting old rpms")
    for rpm in old:
      interface.deleteRpm(rpm)
  
  # download new packages
  if len(new) > 0:
    interface.log(1, "downloading new rpms")
    packages = {} # dict of lists of available rpms
    
    for store in interface.config.mget('//stores/*/store/@id'):
      n,s,d,u,p = interface.getStoreInfo(store)
      
      base = join(s,d)
      
      # get the list of .rpms in the input store
      rpms = spider.find(base, glob='*.[Rr][Pp][Mm]', prefix=False,
                         username=u, password=p)
      for rpm in rpms:
        _,name,version,release,arch = interface.rpmNameDeformat(rpm)
        fullname = '%s-%s-%s' % (name, version, release)
        if not packages.has_key(fullname): packages[fullname] = {}
        if not packages[fullname].has_key(arch): packages[fullname][arch] = []
        packages[fullname][arch].append((n,d,rpm))
    
    # sync new rpms
    tosign = [] # newly synched rpms will be signed
    validarchs = getBaseArch(interface.arch)
    for rpm in new:
      for arch in packages[rpm]:
        if arch in validarchs:
          try:
            store, path, rpmname = packages[rpm][arch][0]
            interface.syncRpm(rpmname, store, path)
            tosign.append(rpmname)
          except IndexError, e:
            self.errlog(1, "No rpm '%s' found in store '%s' for arch '%s'" % (rpm, store, arch))
    
    # sign new packages
    ##args = ['/bin/rpm', '--addsign']
    ##args.extend([join(rpmdir, osutils.basename(rpm)) for rpm in tosign])
    ##os.spawnv(os.P_WAIT, '/bin/rpm', args)
    interface.log(1, "signing new rpms")
    args = ''
    for rpm in tosign: args = args + ' ' + rpm
    shlib.execute('expect -c "spawn /bin/rpm --addsign %s; send timeout -1; ' + \
                             'stty -echo; expect \\"Enter pass phrase: \\"; ' + \
                             'send \\"\\n\\"; expect exp_continue"')
    
    # TODO - if build fails at this point, it will succeed the next time because
    # the file lists are the same.  We need some way to detect if metadata was
    # computed properly
    
    # create repository metadata
    if len(old) > 0 or len(new) > 0: # any package changed
      interface.log(1, "creating repository metadata")
      interface.createrepo()

      # run genhdlist, if anaconda version < 10.92
      if sortlib.dcompare(interface.anaconda_version, '10.92') < 0:
        interface.genhdlist()

class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
