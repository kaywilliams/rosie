import os

from os.path import join, exists

from dims import osutils
from dims import shlib

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'bootiso',
    'requires': ['vmlinuz', 'initrd-file', 'isolinux'],
    'conditional-requires': ['installer-splash', 'isolinux-changed'],
    'parent': 'INSTALLER',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'BootisoHook': 'bootiso',
}


#------ HOOKS ------#
class BootisoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.bootiso'
    
    self.interface = interface
    
    self.isolinux_dir = join(self.interface.SOFTWARE_STORE, 'isolinux')
    self.bootiso = join(self.interface.SOFTWARE_STORE, 'images/boot.iso')
  
  def clean(self):
    self.interface.log(0, "cleaning bootiso event")
    osutils.rm(self.bootiso, force=True)
  
  def check(self):
    return self.interface.cvars['isolinux-changed'] or \
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
