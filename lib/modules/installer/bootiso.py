from os.path import join

import dims.osutils as osutils
import dims.shlib   as shlib

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from lib import FileDownloader, ImageModifier, InstallerInterface

API_VERSION = 3.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'isolinux',
    'interface': 'InstallerInterface',
    'provides': ['isolinux', 'vmlinuz', 'initrd.img', '.buildstamp'],
    'parent': 'INSTALLER',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR    
  },
  {
    'id': 'bootiso',
    'provides': ['boot.iso'],
    'requires': ['vmlinuz', 'initrd.img', 'isolinux', 'splash.lss'],
    'parent': 'INSTALLER',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

#------ HOOK FUNCTIONS ------#
def isolinux_hook(interface):
  interface.log(0, "synchronizing isolinux files")
  i,_,_,d,_,_ = interface.getStoreInfo(interface.getBaseStore())
  
  isolinux_dir = join(interface.getSoftwareStore(), 'isolinux')
  osutils.mkdir(isolinux_dir, parent=True)
  
  # download all files
  dl = FileDownloader(L_FILES, interface)
  dl.download(d,i)
  
  # modify initrd.img
  handler = ImageModifier('initrd.img', interface, INITRD_MD_STRUCT, L_IMAGES)
  if interface.pre(handler):
    interface.modify(handler)

def bootiso_hook(interface):
  interface.log(0, "generating boot.iso")
  
  isolinux_dir = join(interface.getSoftwareStore(), 'isolinux')
  isodir = join(interface.getSoftwareStore(), 'images/isopath')
  isofile = join(interface.getSoftwareStore(), 'images/boot.iso')
  
  osutils.mkdir(isodir, parent=True)
  osutils.cp(isolinux_dir, isodir, recursive=True, link=True)
  shlib.execute('mkisofs -o %s -b isolinux/isolinux.bin -c isolinux/boot.cat '
                '-no-emul-boot -boot-load-size 4 -boot-info-table -RJTV "%s" %s' \
                % (isofile, interface.product, isodir))
  osutils.rm(isodir, recursive=True, force=True)


#------ LOCALS ------#
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
      <file id="boot.msg">
        <path>isolinux</path>
      </file>
      <file id="general.msg">
        <path>isolinux</path>
      </file>
      <file id="initrd.img">
        <path>isolinux</path>
      </file>
      <file id="isolinux.bin">
        <path>isolinux</path>
      </file>
      <file id="isolinux.cfg">
        <path>isolinux</path>
      </file>
      <file id="memtest">
        <path>isolinux</path>
      </file>
      <file id="options.msg">
        <path>isolinux</path>
      </file>
      <file id="param.msg">
        <path>isolinux</path>
      </file>
      <file id="rescue.msg">
        <path>isolinux</path>
      </file>
      <file id="vmlinuz">
        <path>isolinux</path>
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
        <path>isolinux</path>
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
