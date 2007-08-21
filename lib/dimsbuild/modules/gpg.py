from os.path import join

from dims import osutils
from dims import xmltree

from dims.mkrpm.rpmsign import GpgMixin, getPassphrase, signRpm

from dimsbuild.constants import BOOLEANS_TRUE, RPM_GLOB
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'gpgcheck',
    'provides': ['gpg-enabled', 'gpg-status-changed'],
    'interface': 'EventInterface',
  }
]

HOOK_MAPPING = {
  'GpgCheckHook': 'gpgcheck',
  'ValidateHook': 'validate',
}

#------- HOOKS -------#
class GpgCheckHook(GpgMixin):
  def __init__(self, interface):
    GpgMixin.__init__(self)
    
    self.ID = 'gpg.gpgcheck'
    self.VERSION = 0
    self.interface = interface
    self.GPG_DIR = join(self.interface.METADATA_DIR, 'gpg')

    self.DATA = {
      'config': ['/distro/gpgsign', '//gpgkey/text()'],
      'input':  [],
    }
    self.mdfile = join(self.GPG_DIR, 'gpg.md')

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)    
    if not self.interface.config.get('/distro/gpgsign/@enabled', 'False') in BOOLEANS_TRUE:
      self.interface.cvars['gpg-enabled'] = False
      return 
    self.interface.cvars['gpg-enabled'] = True

    # public key
    pubkey = self.interface.cvars['gpg-public-key'] or \
             self.interface.config.get('/distro/gpgsign/gpg-public-key/text()')
    if not pubkey:
      raise GpgError("Missing GPG public key")
    
    # secret key
    seckey = self.interface.cvars['gpg-secret-key'] or \
             self.interface.config.get('/distro/gpgsign/gpg-secret-key/text()')
    if not seckey:
      raise GpgError("Missing GPG secret key")
    
    # password
    password = self.interface.cvars['gpg-passphrase']
    if not password:
      if self.interface.config.pathexists('/distro/gpgsign/gpg-passphrase'):
        password = self.interface.config.get('/distro/gpgsign/gpg-passphrase/text()', '')
      else:
        password = getPassphrase()
    
    # save values so subsequent instantiations don't redo work
    self.interface.cvars['gpg-public-key'] = pubkey
    self.interface.cvars['gpg-secret-key'] = seckey
    self.interface.cvars['gpg-passphrase'] = password
    self.interface.cvars['gpg-homedir']    = join(self.GPG_DIR, '.gnupg')
    
    self.DATA['input'].extend([pubkey, seckey])

  def check(self):
    return self.interface.test_diffs()

  def run(self):
    self.interface.log(0, "checking gpg signature status")
    osutils.mkdir(self.GPG_DIR, parent=True)
    self.interface.cvars['gpg-status-changed'] = True

    if self.interface.has_changed('input') and \
           self.interface.cvars['gpg-public-key'] and \
           self.interface.cvars['gpg-secret-key'] and \
           self.interface.cvars['gpg-homedir']:
      osutils.rm(self.interface.cvars['gpg-homedir'], recursive=True, force=True)
      osutils.mkdir(self.interface.cvars['gpg-homedir'], parent=True)

      # create a home directory for GPG to use. 
      self.importGpgKeys(self.interface.cvars['gpg-public-key'],
                         self.interface.cvars['gpg-secret-key'],
                         homedir=self.interface.cvars['gpg-homedir'])

  def apply(self):
    self.interface.write_metadata()

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'gpg.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/gpgsign', schemafile='gpg.rng')
    

#------ ERRORS ------#
class GpgError: pass
