from os.path import join, exists

import os

import dims.osutils as osutils
import dims.sync    as sync

from callback import BuildSyncCallback
from event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from locals   import printf_local

from lib import InstallerInterface, FileDownloader, ImageModifier, locals_imerge

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'pxeboot',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pxeboot'],
    'requires': ['isolinux'],
    'parent': 'INSTALLER',
  },
]


def pxeboot_hook(interface):
  interface.log(0, "preparing pxeboot images")

  pxeboot_dir  = join(interface.getSoftwareStore(), 'images/pxeboot')
  osutils.mkdir(pxeboot_dir, parent=True)
  
  for file in ['vmlinuz', 'initrd.img']:
    dest = join(pxeboot_dir, file)
    osutils.rm(dest, force=True)
    os.symlink(join('../../isolinux', file), join(pxeboot_dir, file))


INITRD_MD_STRUCT = {
  'config':    ['/distro/main/product/text()',
                '/distro/main/version/text()',
                '/distro/main/fullname/text()',
                '/distro/main/initrd-src/text()'],
  'variables': ['anaconda_version'],
  'input':     ['/distro/main/initrd-src/text()'],
}

L_FILES = ''' 
<locals>
  <files-entries>
    <files version="0">
      <file id="vmlinuz">
        <path>images/pxeboot</path>
      </file>
      <file id="initrd.img">
        <path>images/pxeboot</path>
      </file>
    </files>
  </files-entries>
</locals>
'''

L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="initrd.img">
        <format>ext2</format>
        <zipped>True</zipped>
        <path>images/pxeboot</path>
      </image>
    </images>
    
    <!-- approx 10.2.0.3-1 - initrd.img format changed to cpio -->
    <images version="10.2.0.3-1">
      <action type="update" path="image[@id='initrd.img']">
        <format>cpio</format>
      </action>
    </images>
  </images-entries>
</locals>
'''
