from os.path import join

import dims.osutils as osutils

from dims.mkrpm   import rpmsign
from dims.xmltree import XmlPathError

from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface
from main      import BOOLEANS_TRUE
from output    import OutputEventHandler

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'gpgsign',
    'interface': 'GpgInterface',
    'provides': ['gpgsign'],
    'requires': ['software'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

class GpgInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self._get_gpg_key()
    
    self.rpmdest = join(self.getSoftwareStore(), self.product, 'RPMS') #!
    
  def _get_gpg_key(self):
    if not self.config.get('//gpgsign/sign/text()', 'False') in BOOLEANS_TRUE:
      self.sign = False
      self.pubkey = None
      self.seckey = None
      self.password = None
      return
    else:
      self.sign = True
    
    # public key
    self.pubkey = self.get_cvar('gpg-public-key',
                                self.config.get('//gpgsign/public/text()'))
    if not self.pubkey:
      raise GpgError, "Missing GPG public key"
    
    # secret key
    self.seckey = self.get_cvar('gpg-secret-key',
                                self.config.get('//gpgsign/secret/text()'))
    if not self.seckey:
      raise GpgError, "Missing GPG secret key"
    
    # password
    self.password = self.get_cvar('gpg-passphrase')
    if not self.password:
      if self.config.pathExists('//gpgsign/password'):
        self.password = self.config.get('//gpgsign/password/text()', '')
      else:
        self.password = rpmsign.getPassphrase()
    
    # save values so subsequent instantiations don't redo work
    self.set_cvar('gpg-public-key', self.pubkey)
    self.set_cvar('gpg-secret-key', self.seckey)
    self.set_cvar('gpg-passphrase', self.password)
  
  def sign_rpm(self, rpm):
    "Sign a RPM"
    self.log(2, "signing %s" % rpm)
    rpmsign.signRpm(join(self.rpmdest, rpm),
                    public=self.pubkey,
                    secret=self.seckey,
                    passphrase=self.password)

def presoftware_hook(interface):
  interface.log(0, "checking gpg signature status")
  handler = GpgSignHandler(interface)
  try:
    last_val = handler.configvals['//gpgsign'][0].iget('sign/text()')
  except (AttributeError, IndexError, KeyError, XmlPathError):
    last_val = None
  # if last_val != config.get(...):
  if (last_val in BOOLEANS_TRUE) != \
     (interface.config.get('//gpgsign/sign/text()', 'False') in BOOLEANS_TRUE):
    interface.log(1, "signature status differs; removing rpms")
    osutils.rm(interface.rpmdest, recursive=True, force=True)
    
def pregpgsign_hook(interface):
  handler = GpgSignHandler(interface)
  interface.add_handler('gpgsign', handler)
  
  interface.disableEvent('gpgsign')
  if interface.eventForceStatus('gpgsign') or handler.pre():
    interface.enableEvent('gpgsign')

def gpgsign_hook(interface):
  handler = interface.get_handler('gpgsign')
  handler.handle()

class GpgSignHandler(OutputEventHandler):
  def __init__(self, interface):
    self.interface = interface
    
    data = {
      'config': ['//gpgsign', '//gpgkey/text()'],
    }
    
    self.mdfile = join(interface.getMetadata(), 'gpg.md')
    OutputEventHandler.__init__(self, interface.config, data, self.mdfile)
  
  def pre(self):
    return self.test_input_changed()
  
  def handle(self):
    if self.interface.sign:
      self.interface.log(0, "signing packages")
      for rpm, store in self.interface.get_cvar('new-rpms', []):
        self.interface.sign_rpm(rpm)
    self.write_metadata()

class GpgError: pass
