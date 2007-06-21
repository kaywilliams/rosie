import os

from os.path import join, exists

from dims import osutils
from dims import shlib

from difftest import DiffTest, ConfigHandler, VariablesHandler, InputHandler, OutputHandler
from event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from installer.lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 4.1

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'isolinux',
    'provides': ['vmlinuz', 'initrd.img', '.buildstamp', 'isolinux-changed'],
    'requires': ['anaconda-version', 'source-vars'],
    'parent': 'INSTALLER',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR    
  },
  {
    'id': 'bootiso',
    'requires': ['vmlinuz', 'initrd.img', 'isolinux'],
    'conditional-requires': ['installer-splash', 'isolinux-changed'],
    'parent': 'INSTALLER',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'IsolinuxHook': 'isolinux',
  'BootisoHook':  'bootiso',
}

ISOLINUX_OUTPUT_FILES = [
  'isolinux/boot.msg',
  'isolinux/general.msg',
  'isolinux/initrd.img',
  'isolinux/isolinux.bin',
  'isolinux/isolinux.cfg',
  'isolinux/memtest',
  'isolinux/options.msg',
  'isolinux/param.msg',
  'isolinux/rescue.msg',
  'isolinux/vmlinuz',
]

#------ HOOKS ------#
class IsolinuxHook(ImageModifyMixin, FileDownloadMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.isolinux'
    
    self.interface = interface
    
    self.isolinux_dir = join(self.interface.SOFTWARE_STORE, 'isolinux')
    
    self.DATA = {
      'config':    ['/distro/main/product/text()',
                    '/distro/main/version/text()',
                    '/distro/main/fullname/text()',
                    '/distro/installer/initrd.img/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [interface.config.xpath('/distro/installer/initrd.img/path/text()', [])],
      'output':    [join(interface.SOFTWARE_STORE, x) for x in ISOLINUX_OUTPUT_FILES]
    }
    
    ImageModifyMixin.__init__(self, 'initrd.img', interface, self.DATA)
    FileDownloadMixin.__init__(self, interface)
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def check(self):
    self.register_file_locals(L_FILES)
    self.register_image_locals(L_IMAGES)
    
    return self.interface.isForced('isolinux') or \
           not self.validate_image() or \
           self.test_diffs()
  
  def run(self):
    self.interface.log(0, "synchronizing isolinux files")
    i,_,_,d,_,_ = self.interface.getStoreInfo(self.interface.getBaseStore())
    
    osutils.mkdir(self.isolinux_dir, parent=True)
    
    # download all files - see FileDownloadMixin.download() in lib.py
    self.download(d,i)
    
    # modify initrd.img - see ImageModifyMixin.modify() in lib.py
    self.modify()
    
    self.interface.cvars['isolinux-changed'] = True
  
  def apply(self):
    for file in ISOLINUX_OUTPUT_FILES:
      if not exists(join(self.interface.SOFTWARE_STORE, file)):
        raise RuntimeError, "Unable to find '%s' at '%s'" % (file, join(self.interface.SOFTWARE_STORE))
  

class BootisoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.bootiso'
    
    self.interface = interface
    
    self.isolinux_dir = join(self.interface.SOFTWARE_STORE, 'isolinux')
    self.bootiso = join(self.interface.SOFTWARE_STORE, 'images/boot.iso')
  
  def force(self):
    osutils.rm(self.bootiso, force=True)
  
  def check(self):
    return self.interface.isForced('bootiso') or \
           self.interface.cvars['isolinux-changed'] or \
           not exists(self.bootiso)
  
  def run(self):
    self.interface.log(0, "generating boot.iso")
    
    isodir = join(self.interface.SOFTWARE_STORE, 'images/isopath')
    
    osutils.mkdir(isodir, parent=True)
    osutils.cp(self.isolinux_dir, isodir, recursive=True, link=True)
    
    # apparently mkisofs modifies the mtime of the file it uses as a boot image.
    # to avoid this, we copy the boot image timestamp and overwrite the original
    # when we finish
    isolinux_atime = os.stat(join(self.isolinux_dir, 'isolinux.bin')).st_atime
    isolinux_mtime = os.stat(join(self.isolinux_dir, 'isolinux.bin')).st_mtime
    
    shlib.execute('mkisofs -o %s -b isolinux/isolinux.bin -c isolinux/boot.cat '
                  '-no-emul-boot -boot-load-size 4 -boot-info-table -RJTV "%s" %s' \
                  % (self.bootiso, self.interface.product, isodir))
    os.utime(join(self.isolinux_dir, 'isolinux.bin'), (isolinux_atime, isolinux_mtime))
    osutils.rm(isodir, recursive=True, force=True)
  
  def apply(self):
    if not exists(self.bootiso):
      raise RuntimeError, "Unable to find boot.iso at '%s'" % self.bootiso
  

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
