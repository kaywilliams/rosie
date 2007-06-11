from os.path import join, exists

from dims import osutils

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from main  import locals_imerge

from installer.lib import ImageModifyMixin

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'updates-image',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['updates.img'],
    'requires': ['.buildstamp', 'anaconda-version'],
    'conditional-requires': ['installer-logos'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'UpdatesHook': 'updates-image',
}


#------ HOOKS ------#
class UpdatesHook(ImageModifyMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.updates.updates-image'
    
    self.updatesimage = join(interface.SOFTWARE_STORE, 'images/updates.img')
    
    updates_md_struct = {
      'config':    ['/distro/main/product/text()',
                    '/distro/main/version/text()',
                    '/distro/main/fullname/text()',
                    '/distro/installer/updates.img/path/text()'],
      'variables': ['anaconda_version'],
      'input':     [interface.config.mget('/distro/installer/updates.img/path/text()', [])],
      'output':    [self.updatesimage],
    }
  
    ImageModifyMixin.__init__(self, 'updates.img', interface, updates_md_struct)
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def force(self):
    osutils.rm(self.updatesimage, force=True)
  
  def run(self):
    self.register_image_locals(L_IMAGES)
    
    if not self._test_runstatus(): return
    
    self.interface.log(0, "generating updates.img")
    self.modify() # modify image; see ImageModifyMixin.modify() in lib.py
  
  def apply(self):
    if not exists(self.updatesimage):
      raise RuntimeError, "Unable to find 'updates.img' at '%s'" % self.updatesimage
  
  def _test_runstatus(self):
    return self.interface.isForced('updates-image') or \
           self.check_run_status()


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
