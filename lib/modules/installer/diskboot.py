from os.path import join, exists

import dims.imglib  as imglib
import dims.osutils as osutils

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from installer.lib import InstallerInterface, FileDownloader, ImageModifier, locals_imerge

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'diskboot',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['diskboot'],
    'requires': ['initrd.img', 'splash.lss'],
    'parent': 'INSTALLER',
  },
]


def prediskboot_hook(interface):
  diskboot_md_struct = {
    'config':    ['/distro/main/product/text()',
                  '/distro/main/version/text()',
                  '/distro/main/fullname/text()'],
    'variables': ['anaconda_version'],
    'input':     [join(interface.getSoftwareStore(), 'isolinux/initrd.img'),
                  join(interface.getSoftwareStore(), 'isolinux/splash.lss')],
    'output':    [join(interface.getSoftwareStore(), 'images/diskboot.img')],
  }
  
  # modify image
  handler = DiskbootModifier('diskboot.img', interface, diskboot_md_struct, L_IMAGES)
  interface.add_handler('diskboot.img', handler)
  
  interface.disableEvent('diskboot')
  if interface.eventForceStatus('diskboot') or False:
    interface.enableEvent('diskboot')
  elif interface.get_cvar('isolinux-changed'):
    interface.enableEvent('diskboot')
  elif interface.pre(handler):
    interface.enableEvent('diskboot')

def diskboot_hook(interface):
  interface.log(0, "preparing diskboot image")
  i,_,_,d,_,_ = interface.getStoreInfo(interface.getBaseStore())
  
  diskboot_dir = join(interface.getSoftwareStore(), 'images')
  osutils.mkdir(diskboot_dir, parent=True)
  
  # download file
  dl = FileDownloader(L_FILES, interface)
  dl.download(d,i)
  
  handler = interface.get_handler('diskboot.img')
  interface.modify(handler)


class DiskbootModifier(ImageModifier):
  def __init__(self, name, interface, data, locals, mdfile=None):
    ImageModifier.__init__(self, name, interface, data, locals, mdfile)
  
  def generate(self):
    self.image.write(join(self.interface.getSoftwareStore(), 'isolinux/initrd.img'), '/')
    self.image.write(join(self.interface.getSoftwareStore(), 'isolinux/splash.lss'), '/')


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
