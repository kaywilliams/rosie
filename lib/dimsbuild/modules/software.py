import os
import re
import stat

from rpmUtils.arch import getArchList

from dims import mkrpm
from dims import shlib
from dims import pps

from dims.dispatch import PROPERTY_META

from dimsbuild.constants import RPM_PNVRA
from dimsbuild.event     import Event, RepoMixin #!

API_VERSION = 5.0

P = pps.Path

RPM_PNVRA_REGEX = re.compile(RPM_PNVRA)

class SoftwareMetaEvent(Event):
  def __init__(self): 
    Event.__init__(self,
      id = 'SOFTWARE',
      properties = PROPERTY_META,
    )
    

class SoftwareEvent(Event, RepoMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'software',
      provides = ['gpgsign-passphase', 'rpms', 'rpms-directory',
                  'repodata-directory'],
      requires = ['pkglist', 'repos', 'gpgsign-enabled', 'gpgsign-homedir',
                  'gpgsign-passphrase'],
    )

    self._validarchs = getArchList(self.arch)
    
    self.DATA = {
      'variables': ['cvars[\'pkglist\']',
                    'cvars[\'gpgsign-enabled\']',],
      'input':     [],
      'output':    [],
    }
    
    self.mdfile = self.get_mdfile()
    self.mddir = self.mdfile.dirname
    
    self.builddata_dest = self.mddir/'rpms'
    self.output_dest = self.SOFTWARE_STORE/self.cvars['base-vars']['product']
  
  def _setup(self):
    self.setup_diff(self.mdfile, self.DATA)
 
    input_rpms = set()         # set of rpms to download
    self.repokeys = []         # list of gpgcheck keys to download
    self.rpms_to_check = set() # set of rpms to be checked
    
    for repo in self.getAllRepos():

      # append to list of rpms to download
      for rpminfo in repo.repoinfo:
        rpm = rpminfo['file']
        _,n,v,r,a = self._deformat(rpm)
        nvr = '%s-%s-%s' % (n,v,r)
        if nvr in self.cvars['pkglist'] and a in self._validarchs:
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
          self.rpms_to_check.add(self.builddata_dest/rpm.basename) 

    self.setup_sync(self.builddata_dest, paths=input_rpms, id='cached')
    self.setup_sync(self.mddir, paths=self.repokeys, id='repokeys')    
    self.DATA['variables'].append('rpms_to_check')
    self.setup_sync(self.output_dest, paths=input_rpms, id='output')
    
    if self.cvars['gpgsign-enabled']:
      self.DATA['input'].append(self.cvars['gpgsign-homedir'])
 
  def _clean(self):
    self.remove_output(all=True)
    self.clean_metadata()

  def _check(self):
    return self.test_diffs()
  
  def _run(self):
    self.log(0, "creating software repository")
    if not self.mddir.exists(): self.mddir.mkdirs()

    # remove old output
    self.remove_output()

    # sync rpms to builddata folder
    self.log(1, "caching rpms")
    self.newrpms = self.sync_input(what='cached', link=True)
  
    # gpgcheck rpms
    if self.rpms_to_check:    
      self._gpgcheck_rpms()

    # clean output folder if signing disabled
    if self.var_changed_from_value('cvars[\'gpgsign-enabled\']', True): 
      self.log(1, "removing prior signed rpms")
      self.output_dest.rm(recursive=True, force=True)

    # sync rpms to output folder
    self.log(1, "copying from shared cache")
    newrpms = self.sync_input(copy=True, what='output')

    # sign rpms
    if self.cvars['gpgsign-enabled']:
      self._sign_rpms()

    self.write_metadata()
    
  def _apply(self):
    self.output_dest.mkdirs()
    self.cvars['rpms-directory'] = self.output_dest
    self.cvars['repodata-directory'] = self.SOFTWARE_STORE/'repodata'
    self.cvars['rpms'] = self.list_output(what=['output'])
  
  def _error(self, e):
    # why?
    self._clean()
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
      if self._diff_handlers['input'].diffdict.has_key(key):
        repokeys_changed = True
        break

    if repokeys_changed: 
      new_rpms_to_check = self.rpms_to_check
    else: 
      new_rpms_to_check = self.rpms_to_check.intersection(
                            set(self.newrpms))

    if new_rpms_to_check: 
      self.log(1, "checking signatures")
      self._check_rpm_signatures(sorted(new_rpms_to_check))

  def _check_rpm_signatures(self, new_rpms_to_check):
    # create homedir
    self.sync_input(what='repokeys')
    homedir = self.mddir/'homedir'
    homedir.rm(force=True, recursive=True)
    homedir.mkdirs()
    for key in self.list_output(what='repokeys'):
      shlib.execute('gpg --homedir %s --import %s' %(homedir,key))
    
    # check rpms
    invalids = []
    self.log(1, "checking rpms")    
    for rpm in new_rpms_to_check:
      try:
        self.logger.write(2, rpm.basename, 40)
        mkrpm.VerifyRpm(rpm, homedir=homedir, force=True)
        self.log(None, "OK")
      except mkrpm.RpmSignatureInvalidError:
        self.log(None, "INVALID")
        invalids.append(rpm.basename)
      
    if invalids:
      raise RpmSignatureInvalidError("One or more RPMS failed "\
                                     "GPG key checking: %s" % invalids)
  
  def _sign_rpms(self):
    homedir_changed = False
    for key in self._diff_handlers['input'].diffdict.keys():
      if key.startswith(self.cvars['gpgsign-homedir']):
        homedir_changed = True
        break
    
    if self.var_changed_from_value('cvars[\'gpgsign-enabled\']', False) \
       or homedir_changed:
      rpms_to_sign = self.list_output(what='cached')
    else:
      rpms_to_sign = newrpms
    
    if rpms_to_sign:
      self.log(1, "signing rpms")
      if self.cvars['gpgsign-passphrase'] is None:
        self.cvars['gpgsign-passphrase'] = mkrpm.getPassphrase()
      for rpm_to_sign in rpms_to_sign:
        self.log(2, rpm_to_sign.basename)        
        mkrpm.SignRpm(rpm_to_sign, 
                      homedir=self.cvars['gpgsign-homedir'],
                      passphrase=self.cvars['gpgsign-passphrase'])


class CreaterepoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'createrepo',
      provides = ['repodata-directory'],
      requires = ['rpms'],
      conditionally_requires = ['comps-file'],
    )
    
    self.cvars['repodata-directory'] = self.SOFTWARE_STORE/'repodata'
    
    self.DATA = {
      'variables': ['cvars[\'rpms\']'],
      'output':    [self.cvars['repodata-directory']]
    }
    
    self.mdfile = self.get_mdfile()
  
  def _setup(self):
    self.setup_diff(self.mdfile, self.DATA)
  
  def _clean(self):
    self.remove_output(all=True)
    self.clean_metadata()
  
  def _check(self):
    return self.test_diffs()
  
  def _run(self):
    self.log(0, "running createrepo")
    
    pwd = os.getcwd()
    os.chdir(self.SOFTWARE_STORE)
    self.log(1, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q -g %s .' % self.cvars['comps-file'])
    os.chdir(pwd)
    
    self.write_metadata()
  
  def _error(self, e):
    # why?
    self._clean()

EVENTS = {'MAIN': [SoftwareMetaEvent], 'SOFTWARE': [SoftwareEvent, CreaterepoEvent]}

#------ ERRORS ------#
class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
