from dims import shlib

from dimsbuild.event import Event

API_VERSION = 5.0

class BootisoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'bootiso',
      requires = ['initrd-file', 'isolinux-files'],
      conditionally_requires = ['installer-splash',],
    )
    
    ##self.isolinux_dir = self.SOFTWARE_STORE/'isolinux'
    self.isolinux_dir = self.METADATA_DIR/'isolinux/output/os/isolinux' #! illegal
    self.bootiso = self.SOFTWARE_STORE/'images/boot.iso'
    
    self.DATA = {
      'input':  [self.isolinux_dir],
      'output': [self.bootiso],
    }
  
  def _setup(self):
    self.setup_diff(self.DATA)
  
  def _run(self):
    self.log(0, "generating boot.iso")
    
    isodir = self.SOFTWARE_STORE/'images/isopath'
    
    isodir.mkdirs()
    self.isolinux_dir.cp(isodir, recursive=True, link=True)
    
    # apparently mkisofs modifies the mtime of the file it uses as a boot image.
    # to avoid this, we copy the boot image timestamp and overwrite the original
    # when we finish
    ibin_path = self.isolinux_dir/'isolinux.bin'
    ibin_st = ibin_path.stat()
    
    shlib.execute('mkisofs -o %s -b isolinux/isolinux.bin -c isolinux/boot.cat '
                  '-no-emul-boot -boot-load-size 4 -boot-info-table -RJTV "%s" %s' \
                  % (self.bootiso, self.product, isodir))
    ibin_path.utime((ibin_st.st_atime, ibin_st.st_mtime))
    isodir.rm(recursive=True)
    
    self.write_metadata()
  
  def _apply(self):
    if not self.bootiso.exists():
      raise RuntimeError, "Unable to find boot.iso at '%s'" % self.bootiso

EVENTS = {'INSTALLER': [BootisoEvent]}
