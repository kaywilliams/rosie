from dims.mkrpm.rpmsign import GpgMixin

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'gpg-setup',
    'provides': ['gpg-enabled', 'gpg-keys-changed', 
                 'gpg-public-key', 'gpg-homedir', 'gpg-passphrase'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'GpgSetupHook': 'gpg-setup',
  'ValidateHook': 'validate',
}

#------- HOOKS -------#
class GpgSetupHook(GpgMixin):
  def __init__(self, interface):
    GpgMixin.__init__(self)
    
    self.ID = 'gpg-setup.gpgcheck'
    self.VERSION = 0
    self.interface = interface
    self.mddir = self.interface.METADATA_DIR/'gpg-setup'
    self.gnupg_dir = self.mddir/'.gnupg'
    
    self.interface.cvars['gpg-enabled'] = \
      self.interface.config.pathexists('/distro/gpgsign') and \
      self.interface.config.get('/distro/gpgsign/@enabled', 'True') in BOOLEANS_TRUE
    
    self.DATA = {
      'variables': ['cvars[\'gpg-enabled\']'],
      'config':    [],
      'input':     [],
      'output':    [],
    }
    self.mdfile = self.mddir/'gpg-setup.md'
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA) 
    
    if not self.interface.cvars['gpg-enabled']: return
    
    # config elements
    self.DATA['config'].extend(['/distro/gpgsign/gpg-public-key',
                                '/distro/gpgsign/gpg-secret-key',])
    
    # set pubkey and seckey variables
    #! TODO tighten this up once setup_sync uses xpath as default id
    keys = [ ('public', '/distro/gpgsign/gpg-public-key'),
             ('secret', '/distro/gpgsign/gpg-secret-key') ]
    for name,xpath in keys:
      self.DATA['output'].extend(
        self.interface.setup_sync(xpaths=[(xpath, self.mddir)], id=name))
    
    self.pubkey = self.interface.list_output(what='public')[0]
    self.seckey = self.interface.list_output(what='secret')[0]
   
  def clean(self):
    self.interface.log(0, "cleaning gpg event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()    
  
  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    # changing from gpg-enabled true, cleanup old files and metadata
    if self.interface.var_changed_from_true('cvars[\'gpg-enabled\']'):
      self.clean()
    
    if not self.interface.cvars['gpg-enabled']:
      self.interface.write_metadata()
      return
    
    self.interface.cvars['gpg-keys-changed'] = \
      self.interface.handlers['input'].diffdict
    
    self.interface.log(0, "configuring gpg signing")
    # create a home directory for GPG to use. 
    self.mddir.rm(recursive=True, force=True)
    self.mddir.mkdirs()
    
    # sync keys
    self.interface.sync_input()
    
    # import keys
    self.importKey(self.gnupg_dir, self.pubkey)
    self.importKey(self.gnupg_dir, self.seckey)
    
    # don't leave secret key lying around
    self.seckey.remove()
    
    self.DATA['output'].append(self.gnupg_dir)
    
    self.interface.write_metadata()
  
  def apply(self):
    if self.interface.cvars['gpg-enabled']:
      self.interface.cvars['gpg-homedir']    = self.gnupg_dir
      self.interface.cvars['gpg-public-key'] = self.pubkey
      self.interface.cvars['gpg-passphrase'] = \
        self.interface.config.get('/distro/gpgsign/gpg-passphrase/text()', None)

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'gpg.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/gpgsign', schemafile='gpg.rng')
