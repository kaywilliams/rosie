from dims import mkrpm
from dims import shlib

from dimsbuild.event   import Event
from dimsbuild.logging import L0, L1, L2

API_VERSION = 5.0

class GpgCheckEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgcheck',
      requires = ['cached-rpms', 'repos'],
    )
    
    self.DATA = {
      'variables': [],
      'input':     [],
      'output':    [],
    }
  
  def setup(self):
    self.diff.setup(self.DATA)
    
    self.keys = []      # gpgcheck keys to download
    self.checks = set() # rpms to check
    
    cached = {} # dictionary cached rpms by basename, fullname
    for rpm in self.cvars['cached-rpms']:
      cached[rpm.basename] = rpm
    
    for repo in self.cvars['repos'].values():
      if repo.gpgcheck:
        self.keys.extend(repo.gpgkeys)
        for rpm in [ rpminfo['file'].basename for rpminfo in repo.repoinfo ]:
          if cached.has_key(rpm):
            self.checks.add(cached[rpm])
    
    self.io.setup_sync(self.mddir, paths=self.keys, id='keys')    
    self.DATA['variables'].append('checks')
  
  def run(self):
    self.log(0, L0("running gpgcheck"))
    
    if not self.checks:
      self.io.clean_eventcache(all=True) # remove old keys
      self.diff.write_metadata()
      return
    
    homedir = self.mddir/'homedir'
    self.DATA['output'].append(homedir)
    newkeys = self.io.sync_input() # sync new keys
    
    if newkeys: 
      newchecks = sorted(self.checks)
      homedir.rm(force=True, recursive=True)
      homedir.mkdirs()
      for key in self.io.list_output(what='keys'):
        shlib.execute('gpg --homedir %s --import %s' %(homedir,key))
    else: 
      md, curr = self.diff.handlers['variables'].diffdict['checks']
      if not hasattr(md, '__iter__'): md = set()
      newchecks = sorted(curr.difference(md))
    
    if newchecks: 
      self.log(1, L1("checking signatures"))
      invalids = []
      self.log(1, L1("checking rpms"))
      for rpm in newchecks:
        try:
          self.log(2, L2(rpm.basename+' '), newline=False, format='%(message)-70.70s')
          mkrpm.VerifyRpm(rpm, homedir=homedir, force=True)
          self.logger.write(2, "OK\n")
        except mkrpm.RpmSignatureInvalidError:
          self.logger.write(2, "INVALID\n")
          invalids.append(rpm.basename)
      
      if invalids:
        raise RpmSignatureInvalidError("One or more RPMS failed "
                                       "GPG key checking: %s" % invalids)
    
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()

  def error(self, e):
    self.clean()

EVENTS = {'SOFTWARE': [GpgCheckEvent]}

#------ ERRORS ------#
class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
