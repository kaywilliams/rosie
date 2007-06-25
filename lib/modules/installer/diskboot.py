from os.path import join, exists

from dims import osutils

from difftest import DiffTest, ConfigHandler, VariablesHandler, InputHandler, OutputHandler
from event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from main     import locals_imerge

from installer.lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'diskboot-image',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['diskboot.img'],
    'requires': ['initrd.img'],
    'conditional-requires': ['installer-splash', 'isolinux-changed'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'DiskbootHook': 'diskboot-image',
}


#------ HOOKS ------#
class DiskbootHook(ImageModifyMixin, FileDownloadMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.diskboot.diskboot-image'
    
    self.interface = interface
    
    self.diskbootimage = join(interface.SOFTWARE_STORE, 'images/diskboot.img')
  
    self.DATA = {
      'config':    ['/distro/main/product/text()',
                    '/distro/main/version/text()',
                    '/distro/main/fullname/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [join(interface.SOFTWARE_STORE, 'isolinux/initrd.img')],
      'output':    [self.diskbootimage],
    }
    
    ImageModifyMixin.__init__(self, 'diskboot.img', interface, self.DATA)
    FileDownloadMixin.__init__(self, interface, self.interface.getBaseStore())
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def force(self):
    osutils.rm(self.diskbootimage, force=True)
  
  def check(self):
    self.data['input'].append(self.interface.cvars['installer-splash'])
    self.register_image_locals(L_IMAGES)
    self.register_file_locals(L_FILES)
    
    return self.interface.isForced('diskboot-image') or \
           self.interface.cvars['isolinux-changed'] or \
           not self.validate_image() or \
           self.test_diffs()
  
  def run(self):
    self.interface.log(0, "preparing diskboot image")
    
    diskboot_dir = join(self.interface.SOFTWARE_STORE, 'images')
    osutils.mkdir(diskboot_dir, parent=True)
    
    # download file - see FileDownloadMixin in lib.py
    self.download()
    
    # modify image - see DiskbootModifier, below, and ImageModifyMixin in lib.py
    self.modify()
  
  def apply(self):
    if not exists(self.diskbootimage):
      raise RuntimeError, "Unable to find 'diskboot.img' at '%s'" % self.diskbootimage
  
  def generate(self):
    self.image.write(join(self.interface.SOFTWARE_STORE, 'isolinux/initrd.img'), '/')
    splash = self.interface.cvars.get('installer-splash', None)
    if splash is not None and exists(splash):
      self.image.write(splash, '/')


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
