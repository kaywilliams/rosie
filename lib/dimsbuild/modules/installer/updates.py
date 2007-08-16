from os.path import join, exists

from dims import osutils

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.misc  import locals_imerge

from lib import ImageModifyMixin

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'updates-image',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['updates.img'],
    'requires': ['buildstamp-file', 'anaconda-version'],
    'conditional-requires': ['installer-logos'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'UpdatesHook': 'updates-image',
  'ValidateHook': 'validate',  
}


#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.updates.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/installer/updates.img', 'updates.rng')
    
class UpdatesHook(ImageModifyMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.updates.updates-image'

    self.updatesimage = join(interface.SOFTWARE_STORE, 'images/updates.img')
    
    self.DATA = {
      'config':    ['/distro/installer/updates.img/path/text()'],
      'variables': ['interface.cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [self.updatesimage],
    }
    ImageModifyMixin.__init__(self, 'updates.img', interface, self.DATA)
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def setup(self):
    ImageModifyMixin.setup(self)
    self.register_image_locals(L_IMAGES)
  
  def clean(self):
    self.interface.remove_output(all=True)
  
  def check(self):
    return not self.validate_image() or \
           self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "generating updates.img")
    # clean up old output
    self.clean()
    # modify image
    self.modify() # modify image; see ImageModifyMixin.modify() in lib.py
  
  def apply(self):
    if not exists(self.updatesimage):
      raise RuntimeError, "Unable to find 'updates.img' at '%s'" % self.updatesimage
  
#------ LOCALS ------#
L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="updates.img" virtual="True">
        <format>ext2</format>
        <path>images</path>
      </image>
    </images>
    
    <!-- 11.1.0.11-1 updates.img format changed to cpio, zipped -->
    <images version="11.1.0.11-1">
      <action type="update" path="image[@id='updates.img']">
        <format>cpio</format>
        <zipped>True</zipped>
      </action>
    </images>
  </images-entries>
</locals>
'''
