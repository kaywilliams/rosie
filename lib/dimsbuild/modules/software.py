import os
import re
import stat

from rpmUtils.arch import getArchList

from dims import mkrpm
from dims import shlib
from dims import pps

from dims.shlib          import execute
from dims.mkrpm.rpmsign  import getPassphrase, signRpm
from dimsbuild.constants import RPM_PNVRA
from dimsbuild.event     import EVENT_TYPE_META, EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface

API_VERSION = 4.1

P = pps.Path

#------ EVENTS ------#
EVENTS = [
  {
    'id':        'SOFTWARE',
    'properties': EVENT_TYPE_META,
    'provides': ['software',                 # complete software repository
                 'rpms-directory',           # directory where rpms can be located
                 'rpms']                     # list of rpms in sofware repo
  },
  {
    'id':        'download',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'requires': ['pkglist',                  # to know which rpms to include
                 'repos',],                  # to find rpms in remote repository 
    'provides': ['downloaded-rpms'],         # list of rpms to include in the distribution 
    'parent':    'SOFTWARE',
  },
  {
    'id':        'createrepo',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'requires': ['downloaded-rpms',          # to find rpms to sign                
                 'gpgsign-enabled',          # to know whether to sign rpms
                 'gpgsign-homedir',          # to know where signing keys are located
                 'gpgsign-passphrase'        # for signing rpms
                 ],
    'conditional-requires': ['comps-file'],  # for createrepo
    'provides': ['gpgsign-passphrase',       # if passphrase was not set previously
                                             # software-sign prompts and sets global var
                 'rpms'                      # list of rpms in software repo
                 'rpms-directory',           # directory where rpms can be located
                 'software'],                # complete software repository
                 
    'parent':    'SOFTWARE',
  },
]

HOOK_MAPPING = {
  'SoftwareDownloadHook':   'download',
  'SoftwareCreaterepoHook': 'createrepo',
}

RPM_PNVRA_REGEX = re.compile(RPM_PNVRA)

class SoftwareDownloadHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'software.download'
    
    self.interface = interface
    
    self._validarchs = getArchList(self.interface.arch)
    
    self.DATA = {
      'variables': ['cvars[\'gpgsign-enabled\']',
                    'cvars[\'pkglist\']'],
      'input':     [],
      'output':    [],
    }
    self.mddir = self.interface.METADATA_DIR/'download'
    self.mdfile = self.mddir/'download.md'
    self.download_dest = self.mddir/'rpms'
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    
    paths = []                   # list of rpms to download
    self.repokeys = []           # list of repo gpgkeys
    self.interface.check = set() # set of rpms to be checked
    
    for repo in self.interface.getAllRepos():
      self.repokeys.extend(repo.gpgkeys)
      for rpminfo in repo.repoinfo:
        rpm = rpminfo['file']
        _,n,v,r,a = self.deformat(rpm)
        nvr = '%s-%s-%s' % (n,v,r)
        if nvr in self.interface.cvars['pkglist'] and a in self._validarchs:
          rpm = P(rpminfo['file'])
          if isinstance(rpm, pps.path.http.HttpPath): #! bad        
            rpm._update_stat({'st_size':  rpminfo['size'],
                              'st_mtime': rpminfo['mtime'],
                              'st_mode':  stat.S_IFREG})
          paths.append(rpm)
          if repo.gpgcheck:
            self.interface.check.add(self.download_dest/rpm.basename) 
    self.interface.setup_sync(self.download_dest, paths=paths, id='rpms')
    self.interface.setup_sync(self.mddir, paths=self.repokeys, id='repokeys')    
    self.DATA['variables'].append('check')
  
  def clean(self):
    self.interface.log(0, "cleaning download event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "downloading software packages")

    if not self.mddir.exists(): self.mddir.mkdirs()
    
    self.interface.remove_output()
    
    # sync new rpms
    self.newrpms = self.interface.sync_input(what='rpms', link=True)
  
    # check rpms
    if self.interface.check:    

      repokeys_changed = False
      for key in self.repokeys:
        if self.interface.handlers['input'].diffdict.has_key(key):
          repokeys_changed = True
          break

      if repokeys_changed: 
        checklist = self.interface.check
      else: 
        checklist = self.interface.check.intersection(set(self.newrpms))

      if checklist: self._check_rpm_signatures(sorted(checklist))

    # wrap-up
    self.interface.write_metadata()
  
  def apply(self):
    self.interface.cvars['downloaded-rpms'] = self.interface.list_output(what=['rpms'])

  def error(self, e):
    self.clean()
    self.mddir.rm(force=True, recursive=True)

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

  def _check_rpm_signatures(self, checklist):
    self.interface.log(1, "checking signatures")

    # create homedir
    self.interface.sync_input(what='repokeys')
    homedir = self.mddir/'homedir'
    homedir.rm(force=True, recursive=True)
    homedir.mkdirs()
    for key in self.interface.list_output(what='repokeys'):
      execute('gpg --homedir %s --import %s' %(homedir,key))      
    
    # check rpms
    invalids = []
    self.interface.log(1, "checking rpms")    
    for rpm in checklist:
      try:
        self.interface._base.log.write(2, rpm.basename, 40)
        mkrpm.rpmsign.verifyRpm(rpm, homedir=homedir, force=True)
        self.interface.log(None, "OK")
      except mkrpm.rpmsign.SignatureInvalidException:
        self.interface.log(None, "INVALID")
        invalids.append(rpm.basename)
      
    if invalids:
      raise RpmSignatureInvalidError, "One or more RPMS failed "\
                                      "GPG key checking: %s" % invalids

class SoftwareCreaterepoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'software.createrepo'
    
    self.interface = interface
    
    self.DATA = {
      'variables': ['cvars[\'gpgsign-enabled\']'],
      'input':     [],
      'output':    [],
    }
    self.mddir = self.interface.METADATA_DIR/'createrepo'
    self.mdfile = self.mddir/'createrepo.md'
    self.rpmdest = self.interface.SOFTWARE_STORE/self.interface.BASE_VARS['product']

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    self.interface.setup_sync(self.rpmdest, 
                              paths=self.interface.cvars['downloaded-rpms'], 
                              id='rpms') 
    if self.interface.cvars['gpgsign-enabled']:
      self.DATA['input'].append(self.interface.cvars['gpgsign-homedir'])
 
  def clean(self):
    self.interface.log(0, "cleaning createrepo event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "creating software repository")
    if not self.mddir.exists(): self.mddir.mkdirs()
    
    # remove outdated rpms
    if self.interface.var_changed_from_value('cvars[\'gpgsign-enabled\']', True): 
      self.interface.log(1, "removing prior signed rpms")
      self.interface.remove_output(all=True)
    else:
      self.interface.remove_output()
    
    # sync rpms
    if not self.interface.cvars['gpgsign-enabled']:
      newrpms = self.interface.sync_input(copy=True, link=True, what='rpms')
    else: 
      newrpms = self.interface.sync_input(copy=True, what='rpms')

    # sign rpms
    if self.interface.cvars['gpgsign-enabled']:

      homedir_changed = False
      for key in self.interface.handlers['input'].diffdict.keys():
        if key.startswith(self.interface.cvars['gpgsign-homedir']):
          homedir_changed = True
          break

      if self.interface.var_changed_from_value('cvars[\'gpgsign-enabled\']', False) \
         or homedir_changed:
        signlist = self.interface.list_output(what='rpms')
      else:
        signlist = newrpms

      if signlist:
        self.interface.log(1, "signing rpms")
        if not self.interface.cvars['gpgsign-passphrase']:
          self.interface.cvars['gpgsign-passphrase'] = getPassphrase()
        self.sign_rpms(signlist, 
                       homedir=self.interface.cvars['gpgsign-homedir'],
                       passphrase=self.interface.cvars['gpgsign-passphrase'])

    # wrap-up  
    self.createrepo()
    self.interface.write_metadata()
  
  def apply(self):
    self.rpmdest.mkdirs()
    self.interface.cvars['rpms-directory'] = self.rpmdest
    self.interface.cvars['rpms'] = self.interface.list_output(what=['rpms'])

  def error(self, e):
    self.clean()
    self.mddir.rm(force=True, recursive=True)
    self.rpmdest.rm(force=True, recursive=True)

  def sign_rpms(self, rpms, homedir, passphrase):
    "Sign an RPM"
    for r in rpms:
      self.interface.log(2, r.basename)
      mkrpm.rpmsign.signRpm(r, homedir=homedir, passphrase=passphrase)
  
  def createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.interface.SOFTWARE_STORE)
    self.interface.log(1, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q -g %s .' % self.interface.cvars['comps-file'])
    os.chdir(pwd)

#------ ERRORS ------#
class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
