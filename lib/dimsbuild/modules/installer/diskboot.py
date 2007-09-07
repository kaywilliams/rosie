from dims import filereader

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.misc  import locals_imerge

from lib import ImageModifyMixin

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
class DiskbootHook(ImageModifyMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.diskboot.diskboot-image'
    
    self.interface = interface

    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'config':    ['/distro/installer/diskboot.img'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'diskboot.img', interface, self.DATA)
    
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def setup(self):
    ImageModifyMixin.setup(self)
    self.register_image_locals(L_IMAGES)

    self.DATA['input'].extend([
      self.interface.cvars['installer-splash'],
      self.interface.cvars['initrd-file'],        
    ])

  def clean(self):
    self.interface.log(0, "cleaning diskboot-image event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
  
  def check(self):
    return self.interface.cvars['isolinux-changed'] or \
           not self.validate_image() or \
           self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "preparing diskboot image")
    self.interface.remove_output()
    self.modify()
  
  def apply(self):
    for file in self.interface.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))

  def generate(self):
    ImageModifyMixin.generate(self)
    self.image.write(self.interface.cvars['installer-splash'], '/')
    self.image.write(self.interface.cvars['initrd-file'], '/')
    bootargs = self.interface.config.get('/distro/installer/diskboot.img/boot-args/text()', None)
    if bootargs:      
      if not 'syslinux.cfg' in self.image.list():
        raise RuntimeError("syslinux.cfg not found in the diskboot.img")
      wcopy = self.interface.TEMP_DIR/'syslinux.cfg'
      if wcopy.exists():
        wcopy.remove()
      
      self.image.read('syslinux.cfg', self.interface.TEMP_DIR)
      lines = filereader.read(wcopy)
      for i, line in enumerate(lines):
        if line.strip().startswith('append'):
          break
      
      value = lines.pop(i)
      value = value.strip() + ' ' + bootargs.strip()
      lines.insert(i, value)
      filereader.write(lines, wcopy)
      self.image.write(wcopy, '/')
      wcopy.remove()

#------ LOCALS ------#
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
