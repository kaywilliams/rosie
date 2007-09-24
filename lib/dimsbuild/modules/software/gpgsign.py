from dims import pps
from dims import mkrpm

from dims.mkrpm import GpgMixin

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event
from dimsbuild.logging   import L0, L1, L2

API_VERSION = 5.0

P = pps.Path

class GpgSetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgsign-setup',
      provides = ['gpgsign-enabled', 'gpgsign-public-key',
                  'gpgsign-secret-key', 'gpgsign-passphrase'],
    )
  
  def validate(self):
    self.validator.validate('/distro/gpgsign', 'gpgsign.rng')

  def apply(self):
    self.cvars['gpgsign-enabled'] = \
      self.config.pathexists('/distro/gpgsign') and \
      self.config.get('/distro/gpgsign/@enabled', 'True') in BOOLEANS_TRUE

    self.cvars['gpgsign-public-key'] = \
      self.config.get('/distro/gpgsign/gpg-public-key/text()', None)
    if self.cvars['gpgsign-public-key']:
      P(self.cvars['gpgsign-public-key'])

    self.cvars['gpgsign-secret-key'] = \
      self.config.get('/distro/gpgsign/gpg-secret-key/text()', None)
    if self.cvars['gpgsign-secret-key']:
      P(self.cvars['gpgsign-secret-key'])

    self.cvars['gpgsign-passphrase'] = \
      self.config.get('/distro/gpgsign/gpg-passphrase/text()', None)


class GPGSignEvent(Event, GpgMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgsign',
      requires = ['input-rpms', 'gpgsign-enabled', 'gpgsign-public-key', 
                  'gpgsign-secret-key', 'gpgsign-passphrase'],
      conditionally_comes_after = ['gpgcheck'],
      provides = ['signed-rpms'],
    )
    
    GpgMixin.__init__(self)
    
    self.DATA = {
      'variables': ['cvars[\'gpgsign_enabled\']'],
      'input':     [],
      'output':    [],
    }
  
  def setup(self):
    self.diff.setup(self.DATA)
    
    if not self.cvars['gpgsign-enabled']: return
    
    self.io.setup_sync(self.mddir, paths=self.cvars['gpgsign-public-key'], id='pubkey')
    self.io.setup_sync(self.mddir, paths=self.cvars['gpgsign-secret-key'], id='seckey')
    
    self.io.setup_sync(self.mddir/'rpms', paths=self.cvars['input-rpms'], id='rpms')
  
  def run(self):
    self.log(0, L0("running gpgsign"))
    
    # changing from gpgsign-enabled true, cleanup old files and metadata
    if self.diff.var_changed_from_value('gpgsign_enabled', True):
      self.log(1, L1("gpgsign disabled - cleaning up"))
      self.io.remove_output(all=True)
    
    if not self.cvars['gpgsign-enabled']:
      self.diff.write_metadata()
      return
    
    self.io.remove_output()
    
    self.log(1, L1("configuring gpg signing"))
    # sync keys
    newkeys = self.io.sync_input(what=['pubkey','seckey'])
    
    # import keys
    gnupg_dir = self.mddir / '.gnupg'
    pubkey = self.io.list_output(what='pubkey')[0]
    seckey = self.io.list_output(what='seckey')[0]
    if newkeys:
      gnupg_dir.rm(recursive=True, force=True)
      gnupg_dir.mkdirs()
      self.import_key(gnupg_dir, pubkey)
      self.import_key(gnupg_dir, seckey)
      self.DATA['output'].append(gnupg_dir)
    
    # don't leave secret key lying around
    seckey.remove()
    
    # sync rpms to output folder
    self.log(1, L1("preparing to sign rpms"))
    newrpms = self.io.sync_input(what='rpms')
    
    # sign rpms
    if self.diff.var_changed_from_value('cvars[\'gpgsign-enabled\']', False) \
       or newkeys:
      signrpms = self.io.list_output(what='rpms')
    else:
      signrpms = newrpms
    
    if signrpms:
      self.log(1, L1("signing rpms"))
      if self.config.get('/distro/gpgsign/gpg-passphrase/text()', None) is None:
        self.cvars['gpgsign-passphrase'] = mkrpm.getPassphrase()
      for rpm in signrpms:
        self.log(2, L2(rpm.basename))
        mkrpm.SignRpm(rpm, 
                      homedir=gnupg_dir,
                      passphrase=self.cvars['gpgsign-passphrase'])
    
    self.diff.write_metadata()
  
  def apply(self):
   self.cvars['signed-rpms'] = self.io.list_output(what='rpms')  
  
  def error(self, e):
    self.clean()

EVENTS = {'MAIN': [GpgSetupEvent], 'SOFTWARE': [GPGSignEvent]}
