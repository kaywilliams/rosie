from dims.mkrpm.rpmsign import GpgMixin

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'gpgsign-setup',
    'provides': ['gpgsign-enabled', 'gpgsign-public-key',  
                 'gpgsign-homedir', 'gpgsign-passphrase'],
    'interface': 'EventInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'GpgSetupHook': 'gpgsign-setup',
  'ValidateHook': 'validate',
}

#------- HOOKS -------#
class GpgSetupHook(GpgMixin):
  def __init__(self, interface):
    GpgMixin.__init__(self)
    
    self.ID = 'gpgsign-setup.gpgcheck'
    self.VERSION = 0
    self.interface = interface
    self.mddir = self.interface.METADATA_DIR / 'gpgsign-setup'
    self.gnupg_dir = self.mddir / '.gnupg'
    
    self.interface.cvars['gpgsign-enabled'] = \
      self.interface.config.pathexists('/distro/gpgsign') and \
      self.interface.config.get('/distro/gpgsign/@enabled', 'True') in BOOLEANS_TRUE
    
    self.DATA = {
      'variables': ['cvars[\'gpgsign-enabled\']'],
      'config':    [],
      'input':     [],
      'output':    [],
    }
    self.mdfile = self.mddir / 'gpgsign-setup.md'
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA) 
    
    if not self.interface.cvars['gpgsign-enabled']: return
    
    # config elements
    self.DATA['config'].extend(['/distro/gpgsign/gpg-public-key',
                                '/distro/gpgsign/gpg-secret-key',])
    
    # set pubkey and seckey variables
    #! TODO tighten this up once setup_sync uses xpath as default id
    keys = [ ('public', '/distro/gpgsign/gpg-public-key'),
             ('secret', '/distro/gpgsign/gpg-secret-key') ]
    for name,xpath in keys:
      self.interface.setup_sync(self.mddir, id=name, xpaths=[xpath])
    
    self.pubkey = self.interface.list_output(what='public')[0]
    self.seckey = self.interface.list_output(what='secret')[0]
  
  def clean(self):
    self.interface.log(0, "cleaning gpgsign event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()    
  
  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    if not self.mdfile.dirname.exists(): self.mdfile.dirname.mkdirs()
    
    # changing from gpgsign-enabled true, cleanup old files and metadata
    if self.interface.var_changed_from_value('cvars[\'gpgsign-enabled\']', True):
      self.clean()
    
    if not self.interface.cvars['gpgsign-enabled']:
      self.interface.write_metadata()
      return
    
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
    if self.interface.cvars['gpgsign-enabled']:
      self.interface.cvars['gpgsign-homedir']    = self.gnupg_dir
      self.interface.cvars['gpgsign-public-key'] = self.pubkey
      self.interface.cvars['gpgsign-passphrase'] = \
        self.interface.config.get('/distro/gpgsign/gpg-passphrase/text()', None)


class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'gpg.validate'
    self.interface = interface
  
  def run(self):
    self.interface.validate('/distro/gpgsign', schemafile='gpgsign.rng')
