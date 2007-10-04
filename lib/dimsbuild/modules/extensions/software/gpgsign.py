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
      provides = ['gpgsign-public-key',
                  'gpgsign-secret-key',
                  'gpgsign-passphrase'],
    )
  
  def validate(self):
    self.validator.validate('/distro/gpgsign', 'gpgsign.rng')
  
  def apply(self):
    pubkey = self.config.get('/distro/gpgsign/gpg-public-key/text()', None)
    if pubkey: self.cvars['gpgsign-public-key'] = P(pubkey)
    
    seckey = self.config.get('/distro/gpgsign/gpg-secret-key/text()', None)
    if seckey: self.cvars['gpgsign-secret-key'] = P(seckey)
    
    self.cvars['gpgsign-passphrase'] = \
      self.config.get('/distro/gpgsign/gpg-passphrase/text()', None)


class GPGSignEvent(Event, GpgMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgsign',
      requires = ['input-rpms', 'gpgsign-public-key',
                  'gpgsign-secret-key', 'gpgsign-passphrase'],
      conditionally_comes_after = ['gpgcheck'],
      provides = ['signed-rpms'],
    )
    
    GpgMixin.__init__(self)
    
    self.DATA = {
      'input':     [],
      'output':    [],
    }
  
  def setup(self):
    self.diff.setup(self.DATA)
    
    self.io.setup_sync(self.mddir, paths=self.cvars['gpgsign-public-key'], id='pubkey')
    self.io.setup_sync(self.mddir, paths=self.cvars['gpgsign-secret-key'], id='seckey')
    
    self.io.setup_sync(self.mddir/'rpms', paths=self.cvars['input-rpms'], id='rpms')
  
  def run(self):
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
    if newkeys:
      signrpms = self.io.list_output(what='rpms')
    else:
      signrpms = newrpms
    
    if signrpms:
      self.log(1, L1("signing rpms"))
      if self.cvars['gpgsign-passphrase'] is None:
        self.cvars['gpgsign-passphrase'] = mkrpm.getPassphrase()
      for rpm in signrpms:
        self.log(2, L2(rpm.relpathfrom(self.mddir)), format='%(message).75s')
        mkrpm.SignRpm(rpm,
                      homedir=gnupg_dir,
                      passphrase=self.cvars['gpgsign-passphrase'])
    
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    self.cvars['signed-rpms'] = self.io.list_output(what='rpms')


EVENTS = {'SETUP': [GpgSetupEvent], 'SOFTWARE': [GPGSignEvent]}
