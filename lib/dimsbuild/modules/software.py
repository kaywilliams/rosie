import os
import re
import stat

from rpmUtils.arch import getArchList

from dims import mkrpm
from dims import shlib
from dims import pps

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
                 'rpms-directory',           # rpm folder location
                 'repodata-directory',       # repodata folder location
                 'rpms']                     # list of rpms in sofware repo
  },
  {
    'id':        'software',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'requires': ['pkglist',                  # list of rpms to include
                 'repos',                    # to find rpms in remote repository 
                 'gpgsign-enabled',          # to know whether to sign rpms
                 'gpgsign-homedir',          # to know where signing keys are located
                 'gpgsign-passphrase'        # for signing rpms
                 ],
    'conditional-requires': ['comps-file'],  # for createrepo
    'provides': ['gpgsign-passphrase',       # if passphrase not set previously,
                                             # prompts and sets global var
                 'rpms',                     # list of rpms in software repo
                 'rpms-directory',           # rpms folder location
                 'repodata-directory',       # repodata folder location;
                                             # used by pkgorder
                 'software'],                # complete software repository
                 
    'parent':    'SOFTWARE',
  },
  {
    'id':        'createrepo',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'requires': ['rpms'],                    # list of rpms in distribution
    'conditional-requires': ['comps-file'],  # for createrepo
    'provides': ['repodata-directory'],      # repodata folder location;
                                             # used by pkgorder
    'parent':    'SOFTWARE',
  },
]

HOOK_MAPPING = {
  'SoftwareHook': 'software',
  'CreateRepoHook': 'createrepo',
}

RPM_PNVRA_REGEX = re.compile(RPM_PNVRA)

class SoftwareHook:
  """
  Syncs rpms to builddata (cache=True, link=True), gpgchecks rpms in builddata, 
  syncs rpms to output(cache=True, link=False), and signs rpms
  """

  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'software.software'
    
    self.interface = interface

    self._validarchs = getArchList(self.interface.arch)
    
    self.DATA = {
      'variables': ['cvars[\'pkglist\']',
                    'cvars[\'gpgsign-enabled\']',],
      'input':     [],
      'output':    [],
    }
    self.mddir = self.interface.METADATA_DIR/'software'
    self.mdfile = self.mddir/'software.md'
    self.builddata_dest = self.mddir/'rpms'
    self.output_dest = self.interface.SOFTWARE_STORE/self.interface.BASE_VARS['product']

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
 
    input_rpms = set()                  # set of rpms to download
    self.repokeys = []                  # list of gpgcheck keys to download
    self.interface.rpms_to_check = set() # set of rpms to be checked
    
    for repo in self.interface.getAllRepos():

      # append to list of rpms to download
      for rpminfo in repo.repoinfo:
        rpm = rpminfo['file']
        _,n,v,r,a = self._deformat(rpm)
        nvr = '%s-%s-%s' % (n,v,r)
        if nvr in self.interface.cvars['pkglist'] and a in self._validarchs:
          rpm = P(rpminfo['file'])
          if isinstance(rpm, pps.path.http.HttpPath): #! bad        
            rpm._update_stat({'st_size':  rpminfo['size'],
                              'st_mtime': rpminfo['mtime'],
                              'st_mode':  stat.S_IFREG})
          input_rpms.add(rpm)

      # extend list of gpgkeys to download  
      self.repokeys.extend(repo.gpgkeys)

      # add to set of rpms to be checked
      if repo.gpgcheck:
        repo_rpms =  set([rpminfo['file'] for rpminfo in repo.repoinfo])
        for rpm in repo_rpms.intersection(set(input_rpms)):
          self.interface.rpms_to_check.add(self.builddata_dest/rpm.basename) 

    self.interface.setup_sync(self.builddata_dest, paths=input_rpms, id='cached')
    self.interface.setup_sync(self.mddir, paths=self.repokeys, id='repokeys')    
    self.DATA['variables'].append('rpms_to_check')
    self.interface.setup_sync(self.output_dest, 
                              paths=input_rpms, 
                              id='output') 
    if self.interface.cvars['gpgsign-enabled']:
      self.DATA['input'].append(self.interface.cvars['gpgsign-homedir'])
 
  def clean(self):
    self.interface.log(0, "cleaning software event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "creating software repository")
    if not self.mddir.exists(): self.mddir.mkdirs()

    # sync rpms to builddata folder
    self.interface.log(1, "caching rpms")
    self.newrpms = self.interface.sync_input(what='cached', link=True)
  
    # gpgcheck rpms
    if self.interface.rpms_to_check:    
      self._gpgcheck_rpms()

    # remove outdated rpms from output folder
    if self.interface.var_changed_from_value('cvars[\'gpgsign-enabled\']', True): 
      self.interface.log(1, "removing prior signed rpms")
      self.output_dest.rm(recursive=True, force=True)
    else:
      self.interface.remove_output()
    
    # sync rpms to output folder
    self.interface.log(1, "copying from shared cache")
    newrpms = self.interface.sync_input(copy=True, what='output')

    # sign rpms
    if self.interface.cvars['gpgsign-enabled']:
      self._sign_rpms()

    self.interface.write_metadata()
  
  def apply(self):
    self.output_dest.mkdirs()
    self.interface.cvars['rpms-directory'] = self.output_dest
    self.interface.cvars['repodata-directory'] = self.interface.SOFTWARE_STORE/'repodata'
    self.interface.cvars['rpms'] = self.interface.list_output(what=['output'])

  def error(self, e):
    self.clean()
    self.mddir.rm(force=True, recursive=True)
    self.output_dest.rm(force=True, recursive=True)

  def _deformat(self, rpm):
    """ 
    p[ath],n[ame],v[ersion],r[elease],a[rch] = _deformat(rpm)
    
    Takes an rpm with an optional path prefix and splits it into its component parts.
    Returns a path, name, version, release, arch tuple.
    """
    try:
      return RPM_PNVRA_REGEX.match(rpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, "DEBUG: Unable to extract rpm information from name '%s'" % rpm)
      return (None, None, None, None, None)

  def _gpgcheck_rpms(self):
    repokeys_changed = False
    for key in self.repokeys:
      if self.interface.handlers['input'].diffdict.has_key(key):
        repokeys_changed = True
        break

    if repokeys_changed: 
      new_rpms_to_check = self.interface.rpms_to_check
    else: 
      new_rpms_to_check = self.interface.rpms_to_check.intersection(
                            set(self.newrpms))

    if new_rpms_to_check: 
      self.interface.log(1, "checking signatures")
      self._check_rpm_signatures(sorted(new_rpms_to_check))

  def _check_rpm_signatures(self, new_rpms_to_check):
    # create homedir
    self.interface.sync_input(what='repokeys')
    homedir = self.mddir/'homedir'
    homedir.rm(force=True, recursive=True)
    homedir.mkdirs()
    for key in self.interface.list_output(what='repokeys'):
      shlib.execute('gpg --homedir %s --import %s' %(homedir,key))      
    
    # check rpms
    invalids = []
    self.interface.log(1, "checking rpms")    
    for rpm in new_rpms_to_check:
      try:
        self.interface._base.log.write(2, rpm.basename, 40)
        mkrpm.VerifyRpm(rpm, homedir=homedir, force=True)
        self.interface.log(None, "OK")
      except mkrpm.RpmSignatureInvalidError:
        self.interface.log(None, "INVALID")
        invalids.append(rpm.basename)
      
    if invalids:
      raise RpmSignatureInvalidError("One or more RPMS failed "\
                                     "GPG key checking: %s" % invalids)

  def _sign_rpms(self):
    homedir_changed = False
    for key in self.interface.handlers['input'].diffdict.keys():
      if key.startswith(self.interface.cvars['gpgsign-homedir']):
        homedir_changed = True
        break

    if self.interface.var_changed_from_value('cvars[\'gpgsign-enabled\']', False) \
       or homedir_changed:
      rpms_to_sign = self.interface.list_output(what='cached')
    else:
      rpms_to_sign = newrpms

    if rpms_to_sign:
      self.interface.log(1, "signing rpms")
      if not self.interface.cvars['gpgsign-passphrase']:
        self.interface.cvars['gpgsign-passphrase'] = mkrpm.getPassphrase()
      for rpm_to_sign in rpms_to_sign:
        self.interface.log(2, rpm_to_sign.basename)        
        mkrpm.SignRpm(rpm_to_sign, 
                      homedir=self.interface.cvars['gpgsign-homedir'],
                      passphrase=self.interface.cvars['gpgsign-passphrase'])

        
class CreateRepoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'software.createrepo'
    
    self.interface = interface

    self.interface.cvars['repodata-directory'] = \
      self.interface.SOFTWARE_STORE/'repodata'
  
    self.DATA = {
      'variables': ['cvars[\'rpms\']'],
      'output':    [self.interface.cvars['repodata-directory']]
    }

    self.mdfile = self.interface.METADATA_DIR/'software.md'

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
 
  def clean(self):
    self.interface.log(0, "cleaning createrepo event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "running createrepo event")

    pwd = os.getcwd()
    os.chdir(self.interface.SOFTWARE_STORE)
    self.interface.log(1, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q -g %s .' % self.interface.cvars['comps-file'])
    os.chdir(pwd)

    self.interface.write_metadata()

  def error(self, e):
    self.clean()

#------ ERRORS ------#
class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
