import re
import os

from os.path       import exists, join
from rpmUtils.arch import getArchList

from dims import osutils
from dims import mkrpm
from dims import shlib
from dims import sortlib
from dims import spider
from dims import sync

from dimsbuild.constants import BOOLEANS_TRUE, RPM_GLOB, RPM_PNVRA
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'software',
    'interface': 'SoftwareInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['rpms-directory', 'new-rpms'],
    'requires': ['pkglist', 'anaconda-version', 'repo-contents', 'gpg-status-changed'],
    'conditional-requires': ['comps-file', 'RPMS'],
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
    
    self.rpmdest = join(self.SOFTWARE_STORE, self.product)

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
    self.log(1, "signing rpms")
    for r in rpms:
      self.log(2, osutils.basename(r))
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
      'input':  [],
      'output': [],
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'software.md')
    
  def setup(self):
    # for each rpm in the pkglist, find the RPM's timestamp and size
    # from the repo's primary.xml.gz and add the (rpm, size, mtime)
    # 3-tuple to the input file's list.
    paths = []
    for repo in self.interface.getAllRepos():
      for rpminfo in repo.repoinfo:
        rpm = rpminfo['file']
        size = rpminfo['size']
        mtime = rpminfo['mtime']
        _,n,v,r,a = self.interface.deformat(rpm)
        nvr = '%s-%s-%s' % (n,v,r)
        if nvr in self.interface.cvars['pkglist'] and \
               a in self._validarchs:
          paths.append(((rpm, size, mtime), self.interface.rpmdest))
    
    self.DATA['input'].append(self.interface.cvars['pkglist-file'])
    self.DATA['input'].append(join(self.interface.METADATA_DIR, 'repos'))
    self.interface.setup_diff(self.mdfile, self.DATA)
    
    i,o = self.interface.setup_sync(paths=paths)
    self.DATA['input'].extend(i)
    self.DATA['output'].extend(o)
    
  def clean(self):
    self.interface.log(0, "cleaning software event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.cvars['gpg-status-changed'] or \
           not exists(self.interface.rpmdest) or \
           self.interface.test_diffs()
  
  def run(self):
    "Build a software store"
    if self.interface.cvars['gpg-status-changed'] and \
           exists(self.interface.rpmdest):
      self.interface.log(0, "deleting old rpms")
      self.interface.remove_output(all=True)
    else:
      self.interface.remove_output()

    self.interface.log(0, "processing rpms")
    newrpms = self.interface.sync_input()
    if newrpms:
      newrpms.sort()
      if self.interface.cvars['gpg-enabled']:
        self.interface.sign_rpms(newrpms, homedir=self.interface.cvars['gpg-homedir'],
                                 passphrase=self.interface.cvars['gpg-passphrase'])
      self.interface.createrepo()
      self.interface.cvars['new-rpms'] = newrpms

    self.interface.write_metadata()
    
  def apply(self):
    osutils.mkdir(self.interface.rpmdest, parent=True)
    self.interface.cvars['rpms-directory'] = self.interface.rpmdest

