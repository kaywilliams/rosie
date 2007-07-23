from os.path import join, exists

from dims import osutils

from dimsbuild.event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.misc     import locals_imerge

from lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'diskboot-image',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['diskboot.img'],
    'requires': ['initrd-file', 'buildstamp-file'],
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
      'variables': ['interface.cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [self.diskbootimage],
    }
    
    ImageModifyMixin.__init__(self, 'diskboot.img', interface, self.DATA)
    FileDownloadMixin.__init__(self, interface, self.interface.getBaseRepoId())
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def setup(self):
    ImageModifyMixin.setup(self)
    self.register_image_locals(L_IMAGES)
    self.register_file_locals(L_FILES)

    self.update({
     'input': [
        self.interface.cvars['installer-splash'],
        self.interface.cvars['initrd-file'],        
      ],
    })
  
  def force(self):
    self.interface.log(0, "forcing diskboot-image")
    self.remove_files(self.handlers['output'].oldoutput.keys())
  
  def check(self):
    if self.interface.cvars['isolinux-changed'] or \
           self.interface.isForced('diskboot-image') or \
           not self.validate_image() or \
           self.test_diffs():
      if not self.interface.isForced('diskboot-image'):
        self.interface.log(0, "cleaning diskboot-image")
        self.remove_files(self.handlers['output'].oldoutput.keys())
      return True
    else:
      return False
  
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
    ImageModifyMixin.generate(self)
    self.add_file(self.interface.cvars['installer-splash'], '/')
    self.add_file(self.interface.cvars['initrd-file'], '/')

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
