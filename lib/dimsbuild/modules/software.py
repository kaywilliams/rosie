import re
import os

from rpmUtils.arch import getArchList

from dims import mkrpm
from dims import shlib

from dims.mkrpm.rpmsign  import getPassphrase, signRpm
from dimsbuild.constants import RPM_PNVRA
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface

API_VERSION = 4.1

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'software',
    'interface': 'SoftwareInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'requires': ['pkglist',                  # to know which rpms to include
                 'repos',                    # to find rpms in remote repository AND
                                             # to find gpg homedirs for checksig
                 'gpgsign-enabled',          # to know whether to sign rpms
                 'gpgsign-keys-changed',     # to know whether to resign rpms
                 'gpgsign-homedir',          # to know where signing keys are located
                 'gpgsign-passphrase'        # for signing rpms
                 ],
    'conditional-requires': ['comps-file',   # for createrepo
                             'RPMS',],       # for auto generated rpms
    'provides': ['rpms-directory', 
                 'rpms',                     # list of rpms included in the distribution
                 'gpgsign-passphrase'        # if passphrase was not set previously
                                             # software promps for it and sets global var
                ],
  },
]

HOOK_MAPPING = {
  'SoftwareHook': 'software',
}

RPM_PNVRA_REGEX = re.compile(RPM_PNVRA)


#------ INTERFACES ------#
class SoftwareInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    
    self.rpmdest = self.SOFTWARE_STORE/self.product
  
  def rpmCheckSignature(self, rpm, homedir, verbose=True):
    "Check RPM signature's validity.  Raises mkrpm.rpmsign.SignatureInvalidException"
    if verbose:
      self._base.log.write(2, rpm.basename, 40)
    mkrpm.rpmsign.verifyRpm(rpm, homedir=homedir, force=True)
  
  def deformat(self, rpm):
    """ 
    p[ath],n[ame],v[ersion],r[elease],a[rch] = SoftwareInterface.deformat(rpm)
    
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
    _,n,v,r,_ = self.deformat(rpm)
    return '%s-%s-%s' % (n,v,r)
  
  def sign_rpms(self, rpms, homedir, passphrase):
    "Sign an RPM"
    for r in rpms:
      self.log(2, r.basename)
      mkrpm.rpmsign.signRpm(r, homedir=homedir, passphrase=passphrase)
  
  def createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.SOFTWARE_STORE)
    self.log(1, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q -g %s .' % self.cvars['comps-file'])
    os.chdir(pwd)
  
  def genhdlist(self):
    "Run genhdlist on the output store.  Only necesary in some versions of anaconda"
    self.log(1, "running genhdlist")
    shlib.execute('/usr/lib/anaconda-runtime/genhdlist --productpath %s %s' % \
                  (self.product, self.SOFTWARE_STORE))


#------ HOOKS ------#
class SoftwareHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'software.software'
    
    self.interface = interface
    
    self._validarchs = getArchList(self.interface.arch)
    
    self.DATA = {
      'variables': ['cvars[\'gpgsign-enabled\']',
                    'cvars[\'pkglist\']'],
      'input':     [],
      'output':    [],
    }
    self.mdfile = self.interface.METADATA_DIR/'software.md'
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    
    paths = [] # list of rpms to download
    
    self.interface.checksig = {} # dictionary of rpms and associated gpgkey homedir
                                 # interface variable so it can be saved in metadata
    
    self.homedirs = [] # list of gpgkey homedirs
    
    for repo in self.interface.getAllRepos():
      homedir = repo.ljoin('homedir')
      #populate homedir var
      if homedir.exists(): self.homedirs.append(homedir)
      #populate rpms and checksig vars
      for rpminfo in repo.repoinfo:
        rpm = rpminfo['file']
        _,n,v,r,a = self.interface.deformat(rpm)
        nvr = '%s-%s-%s' % (n,v,r)
        if nvr in self.interface.cvars['pkglist'] and \
               a in self._validarchs:
          paths.append(rpm)
          if repo.gpgcheck:
            self.interface.checksig[self.interface.rpmdest/rpm.basename] = homedir
    
    self.DATA['input'].extend(self.homedirs)

    self.interface.setup_sync(self.interface.rpmdest, paths=paths, id='rpms')
    
    self.DATA['variables'].append('checksig')
  
  def clean(self):
    self.interface.log(0, "cleaning software event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.cvars['gpgsign-keys-changed'] or \
      self.interface.test_diffs()
  
  def run(self):
    "Build a software store"
    self.interface.log(0, "processing rpms")
    
    # determine if gpg homedirs changed
    homedirs_changed = False
    for homedir in self.homedirs:
      for file in self.interface.handlers['input'].diffdict.keys():
        if file.startswith(homedir):
          homedirs_changed = True
          break
    
    # changing from gpgsign-enabled, or gpgsign-enabled and checkkeys changed
    # remove all rpms from output store
    if self.interface.var_changed_from_true('cvars[\'gpgsign-enabled\']') or \
      (self.interface.cvars['gpgsign-enabled'] and homedirs_changed):
      self.interface.remove_output(all=True)
    # otherwise, remove only outdated rpms
    else:
      self.interface.remove_output()
    
    # sync new rpms
    self.newrpms = self.interface.sync_input()
    
    # check signatures
    ##if self.newrpms and self.interface.checksig:
    ##  self._check_rpm_signatures()
    
    
    # sign rpms
    if self.interface.cvars['gpgsign-keys-changed']:
      self.newrpms = self.interface.list_output()
    
    if self.newrpms:
      self.newrpms.sort()
      if self.interface.cvars['gpgsign-enabled']:
        self.interface.log(1, "signing rpms")
        if not self.interface.cvars['gpgsign-passphrase']:
          self.interface.cvars['gpgsign-passphrase'] = getPassphrase()
        self.interface.sign_rpms(self.newrpms, 
                                 homedir=self.interface.cvars['gpgsign-homedir'],
                                 passphrase=self.interface.cvars['gpgsign-passphrase'])
      
      self.interface.createrepo()
    
    self.interface.write_metadata()
  
  def apply(self):
    self.interface.rpmdest.mkdirs()
    self.interface.cvars['rpms-directory'] = self.interface.rpmdest
    self.interface.cvars['rpms'] = self.interface.list_output(what=['rpms'])

  def _check_rpm_signatures(self):
    self.interface.log(1, "checking signatures")
    
    invalids = []
    for rpm in self.newrpms:
      if self.interface.checksig.has_key(rpm):
        try:
          self.interface.rpmCheckSignature(rpm, self.interface.checksig[rpm])
          self.interface.log(None, "OK")
        except mkrpm.rpmsign.SignatureInvalidException:
          self.interface.log(None, "INVALID")
          invalids.append(rpm.basename)
      
      if invalids:
        raise RpmSignatureInvalidError, "One or more RPMS failed GPG key checking: %s" % invalids
