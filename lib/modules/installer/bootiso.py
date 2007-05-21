import os

from os.path import join

import dims.osutils as osutils
import dims.shlib   as shlib

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from installer.lib import FileDownloader, ImageModifier, InstallerInterface

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
def preisolinux_hook(interface):
  bootiso_md_struct = {
    'config':    ['/distro/main/product/text()',
                  '/distro/main/version/text()',
                  '/distro/main/fullname/text()',
                  '/distro/installer/product.img/path/text()'],
    'variables': ['anaconda_version'],
    'input':     [interface.config.mget('/distro/installer/initrd.img/path/text()', [])],
    'output':    [join(interface.getSoftwareStore(), 'isolinux/boot.msg'),
                  join(interface.getSoftwareStore(), 'isolinux/general.msg'),
                  join(interface.getSoftwareStore(), 'isolinux/initrd.img'),
                  join(interface.getSoftwareStore(), 'isolinux/isolinux.bin'),
                  join(interface.getSoftwareStore(), 'isolinux/isolinux.cfg'),
                  join(interface.getSoftwareStore(), 'isolinux/memtest'),
                  join(interface.getSoftwareStore(), 'isolinux/options.msg'),
                  join(interface.getSoftwareStore(), 'isolinux/param.msg'),
                  join(interface.getSoftwareStore(), 'isolinux/rescue.msg'),
                  join(interface.getSoftwareStore(), 'isolinux/vmlinuz')],
  }
  
  handler = ImageModifier('initrd.img', interface, bootiso_md_struct, L_IMAGES)
  interface.add_handler('initrd.img', handler)
  
  interface.disableEvent('isolinux')
  if interface.eventForceStatus('isolinux') or False:
    interface.enableEvent('isolinux')
  elif interface.pre(handler):
    interface.enableEvent('isolinux')
  

def isolinux_hook(interface):
  interface.log(0, "synchronizing isolinux files")
  i,_,_,d,_,_ = interface.getStoreInfo(interface.getBaseStore())
  
  isolinux_dir = join(interface.getSoftwareStore(), 'isolinux')
  osutils.mkdir(isolinux_dir, parent=True)
  
  # download all files
  dl = FileDownloader(L_FILES, interface)
  dl.download(d,i)
  
  # modify initrd.img
  handler = interface.get_handler('initrd.img')
  interface.modify(handler)
  
  interface.set_cvar('isolinux-changed', True)

def prebootiso_hook(interface):
  interface.disableEvent('bootiso')
  
  if interface.eventForceStatus('bootiso') or False:
    interface.enableEvent('bootiso')
  elif interface.get_cvar('isolinux-changed'):
    interface.enableEvent('bootiso')

def bootiso_hook(interface):
  interface.log(0, "generating boot.iso")
  
  isolinux_dir = join(interface.getSoftwareStore(), 'isolinux')
  isodir = join(interface.getSoftwareStore(), 'images/isopath')
  isofile = join(interface.getSoftwareStore(), 'images/boot.iso')
  
  osutils.mkdir(isodir, parent=True)
  osutils.cp(isolinux_dir, isodir, recursive=True, link=True)
  # apparently mkisofs modifies the mtime of the file it uses as a boot image.
  # to avoid this, we copy the boot image timestamp and overwrite the original
  # when we finish
  isolinux_atime = os.stat(join(isolinux_dir, 'isolinux.bin')).st_atime
  isolinux_mtime = os.stat(join(isolinux_dir, 'isolinux.bin')).st_mtime
  shlib.execute('mkisofs -o %s -b isolinux/isolinux.bin -c isolinux/boot.cat '
                '-no-emul-boot -boot-load-size 4 -boot-info-table -RJTV "%s" %s' \
                % (isofile, interface.product, isodir))
  os.utime(join(isolinux_dir, 'isolinux.bin'), (isolinux_atime, isolinux_mtime))
  osutils.rm(isodir, recursive=True, force=True)


#------ LOCALS ------#
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
