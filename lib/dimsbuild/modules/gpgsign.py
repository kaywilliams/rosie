from dims.mkrpm import GpgMixin

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event

API_VERSION = 5.0

#------- HOOKS -------#
class GpgSetupEvent(Event, GpgMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgsign-setup',
      provides = ['gpgsign-enabled', 'gpgsign-public-key',
                  'gpgsign-homedir', 'gpgsign-passphrase'],
    )
    
    GpgMixin.__init__(self)
    
    self.gnupg_dir = self.mddir / '.gnupg'
    
    self.cvars['gpgsign-enabled'] = \
      self.config.pathexists('/distro/gpgsign') and \
      self.config.get('/distro/gpgsign/@enabled', 'True') in BOOLEANS_TRUE
    
    self.DATA = {
      'variables': ['cvars[\'gpgsign-enabled\']'],
      'config':    [],
      'input':     [],
      'output':    [],
    }
  
  def _validate(self):
    self.validate('/distro/gpgsign', 'gpgsign.rng')
  
  def _setup(self):
    self.setup_diff(self.DATA) 
    
    if not self.cvars['gpgsign-enabled']: return
    
    # config elements
    self.DATA['config'].extend(['/distro/gpgsign/gpg-public-key',
                                '/distro/gpgsign/gpg-secret-key',])
    
    # set pubkey and seckey variables
    #! TODO tighten this up once setup_sync uses xpath as default id
    keys = [ ('public', '/distro/gpgsign/gpg-public-key'),
             ('secret', '/distro/gpgsign/gpg-secret-key') ]
    for name,xpath in keys:
      self.setup_sync(self.mddir, id=name, xpaths=[xpath])
    
    self.pubkey = self.list_output(what='public')[0]
    self.seckey = self.list_output(what='secret')[0]
  
  def _run(self):
    # changing from gpgsign-enabled true, cleanup old files and metadata
    if self.var_changed_from_value('cvars[\'gpgsign-enabled\']', True):
      self._clean()
    
    if not self.cvars['gpgsign-enabled']:
      self.write_metadata()
      return
    
    self.log(0, "configuring gpg signing")
    # create a home directory for GPG to use. 
    self.mddir.rm(recursive=True, force=True)
    self.mddir.mkdirs()
    
    # sync keys
    self.sync_input()
    
    # import keys
    self.import_key(self.gnupg_dir, self.pubkey)
    self.import_key(self.gnupg_dir, self.seckey)
    
    # don't leave secret key lying around
    self.seckey.remove()
    
    self.DATA['output'].append(self.gnupg_dir)
    
    self.write_metadata()
  
  def _apply(self):
    if self.cvars['gpgsign-enabled']:
      self.cvars['gpgsign-homedir']    = self.gnupg_dir
      self.cvars['gpgsign-public-key'] = self.pubkey
      self.cvars['gpgsign-passphrase'] = \
        self.config.get('/distro/gpgsign/gpg-passphrase/text()', None)

EVENTS = {'MAIN': [GpgSetupEvent]}
