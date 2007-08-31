from dims import shlib

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.1

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
    
    self.isolinux_dir = self.interface.SOFTWARE_STORE/'isolinux'
    self.bootiso = self.interface.SOFTWARE_STORE/'images/boot.iso'
  
  def clean(self):
    self.interface.log(0, "cleaning bootiso event")
    self.bootiso.rm(force=True)
  
  def check(self):
    return self.interface.cvars['isolinux-changed'] or \
           not self.bootiso.exists()
  
  def run(self):
    self.interface.log(0, "generating boot.iso")
    
    isodir = self.interface.SOFTWARE_STORE/'images/isopath'
    
    isodir.mkdirs()
    self.isolinux_dir.cp(isodir, recursive=True, link=True)
    
    # apparently mkisofs modifies the mtime of the file it uses as a boot image.
    # to avoid this, we copy the boot image timestamp and overwrite the original
    # when we finish
    ibin_path = self.isolinux_dir/'isolinux.bin'
    ibin_st = ibin_path.stat()
    
    shlib.execute('mkisofs -o %s -b isolinux/isolinux.bin -c isolinux/boot.cat '
                  '-no-emul-boot -boot-load-size 4 -boot-info-table -RJTV "%s" %s' \
                  % (self.bootiso, self.interface.product, isodir))
    ibin_path.utime((ibin_st.st_atime, ibin_st.st_mtime))
    isodir.rm(recursive=True)
  
  def apply(self):
    if not self.bootiso.exists():
      raise RuntimeError, "Unable to find boot.iso at '%s'" % self.bootiso
