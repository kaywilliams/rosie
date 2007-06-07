from os.path import join, exists

from dims import osutils

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from main  import locals_imerge

from installer.lib import FileDownloader, ImageModifier

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'diskboot',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['diskboot'],
    'requires': ['initrd.img'],
    'conditional-requires': ['splash.lss'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'DiskbootHook': 'diskboot',
}


#------ HOOKS ------#
class DiskbootHook(ImageModifier, FileDownloader):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'diskboot.diskboot'
    
    self.interface = interface
    
    self.diskbootimage = join(interface.SOFTWARE_STORE, 'images/diskboot.img')
  
    diskboot_md_struct = {
      'config':    ['/distro/main/product/text()',
                    '/distro/main/version/text()',
                    '/distro/main/fullname/text()'],
      'variables': ['anaconda_version'],
      'input':     [join(interface.SOFTWARE_STORE, 'isolinux/initrd.img'),
                    join(interface.SOFTWARE_STORE, 'isolinux/splash.lss')],
      'output':    [self.diskbootimage],
    }
    
    ImageModifier.__init__(self, 'diskboot.img', interface, diskboot_md_struct)
    FileDownloader.__init__(self, interface)
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def force(self):
    osutils.rm(self.diskbootimage, force=True)
  
  def run(self):
    self.register_image_locals(L_IMAGES)
    self.register_file_locals(L_FILES)
    
    if not self._test_runstatus(): return    
    
    self.interface.log(0, "preparing diskboot image")
    i,_,_,d,_,_ = self.interface.getStoreInfo(self.interface.getBaseStore())
    
    diskboot_dir = join(self.interface.SOFTWARE_STORE, 'images')
    osutils.mkdir(diskboot_dir, parent=True)
    
    # download file - see FileDownloader in lib.py
    self.download(d,i)
    
    # modify image - see DiskbootModifier, below, and ImageModifier in lib.py
    self.modify()
  
  def apply(self):
    if not exists(self.diskbootimage):
      raise RuntimeError, "Unable to find 'diskboot.img' at '%s'" % self.diskbootimage
  
  def _test_runstatus(self):
    return self.interface.isForced('diskboot') or \
           self.interface.get_cvar('isolinux-changed') or \
           self.check_run_status()

  def generate(self):
    self.image.write(join(self.interface.SOFTWARE_STORE, 'isolinux/initrd.img'), '/')
    if exists(join(self.interface.SOFTWARE_STORE, 'isolinux/splash.lss')):
      self.image.write(join(self.interface.SOFTWARE_STORE, 'isolinux/splash.lss'), '/')


#------ LOCALS ------#
L_FILES = ''' 
<locals>
  <files-entries>
    <files version="0">
      <file id="diskboot.img">
        <path>images</path>
      </file>
    </files>
  </files-entries>
</locals>
'''

L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="diskboot.img">
        <format>fat32</format>
        <path>images</path>
      </image>
    </images>
  </images-entries>
</locals>
'''
