from os.path import join

from dims import osutils
from dims import xmltree

from dims.mkrpm   import rpmsign

from dimsbuild.constants import BOOLEANS_TRUE, RPM_GLOB
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import DiffMixin, EventInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'gpgsign',
    'interface': 'GpgInterface',
    'requires': ['rpms-directory'],
    'conditional-requires': ['new-rpms', 'software'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'SoftwareHook': 'software',
  'GpgsignHook':  'gpgsign',
  'ValidateHook': 'validate',
}

class GpgInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self._get_gpg_key()
    
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
    self.pubkey = self.cvars['gpg-public-key'] or \
                  self.config.get('//gpgsign/public/text()')
    if not self.pubkey:
      raise GpgError, "Missing GPG public key"
    
    # secret key
    self.seckey = self.cvars['gpg-secret-key'] or \
                  self.config.get('//gpgsign/secret/text()')
    if not self.seckey:
      raise GpgError, "Missing GPG secret key"
    
    # password
    self.password = self.cvars['gpg-passphrase']
    if not self.password:
      if self.config.pathexists('//gpgsign/password'):
        self.password = self.config.get('//gpgsign/password/text()', '')
      else:
        self.password = rpmsign.getPassphrase()
    
    # save values so subsequent instantiations don't redo work
    self.cvars['gpg-public-key'] = self.pubkey
    self.cvars['gpg-secret-key'] = self.seckey
    self.cvars['gpg-passphrase'] = self.password
  
  def sign_rpm(self, rpm):
    "Sign a RPM"
    self.log(2, "signing %s" % rpm)
    rpmsign.signRpm(join(self.cvars['rpms-directory'], rpm),
                    public=self.pubkey,
                    secret=self.seckey,
                    passphrase=self.password)


class SoftwareHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'gpg.software'
    
    self.interface = interface

  def pre(self):
    # TODO - check if we can remove RPM signatures more easily without actually
    # deleting the entire RPM
    self.interface.log(0, "checking gpg signature status")
    try:
      # the following is kind of a hack - read gpg's metadata and compare the value
      # of the sign element to that in the config file
      mdfile = xmltree.read(join(self.interface.METADATA_DIR, 'gpg.md'))
      elem = mdfile.get('//config/value[@path="//gpgsign"]/elements')
      last_val = elem.get('gpgsign/sign/text()')
    except (AttributeError, xmltree.XmlPathError, ValueError):
      last_val = None
    
    # the following is roughly equivalent to 'if last_val != config.get(...):'
    if (last_val in BOOLEANS_TRUE) != \
       (self.interface.config.get('//gpgsign/sign/text()', 'False') in BOOLEANS_TRUE):
      self.interface.log(1, "signature status differs; removing rpms")
      osutils.rm(self.interface.rpmdest, recursive=True, force=True)


class GpgsignHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'gpg.gpgsign'
    
    self.interface = interface

    self.DATA =  {
      'config': ['//gpgsign', '//gpgkey/text()'],
    }
    self.mdfile = join(interface.METADATA_DIR, 'gpg.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
  
  def force(self):
    self.interface.cvars['gpg-tosign'] or \
                            [ (x, None) for x in \
                              osutils.find(self.interface.cvars['rpms-directory'],
                                           maxdepth=1,
                                           name=RPM_GLOB,
                                           type=osutils.TYPE_FILE,
                                           prefix=False) ]
  
  def check(self):
    return self.interface.isForced('gpgsign') or \
           self.test_diffs()
    
  def run(self):
    if self.interface.sign:
      self.interface.log(0, "signing packages")
      for rpm,_ in (self.interface.cvars['new-rpms'] or []) + \
                   (self.interface.cvars['gpg-tosign'] or []):
        self.interface.sign_rpm(rpm)
  
  def apply(self):
    self.write_metadata()
  

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'gpg.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('//gpgsign', schemafile='gpg.rng')
    

#------ ERRORS ------#
class GpgError: pass
