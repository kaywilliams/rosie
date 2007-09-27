from dims import shlib

from dimsbuild.event   import Event
from dimsbuild.logging import L0

API_VERSION = 5.0

class BootisoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'bootiso',
      requires = ['initrd-file', 'isolinux-dir'],
      conditionally_requires = ['installer-splash',],
    )
    
    self.bootiso = self.SOFTWARE_STORE/'images/boot.iso'
    
    self.DATA = {
      'input':  [],
      'output': [self.bootiso],
    }
  
  def setup(self):
    self.diff.setup(self.DATA)
    self.DATA['input'].append(self.cvars['isolinux-dir'])
  
  def run(self):
    self.log(0, L0("generating boot.iso"))
    
    isodir = self.SOFTWARE_STORE/'images/isopath'
    
    isodir.mkdirs()
    self.cvars['isolinux-dir'].cp(isodir, recursive=True, link=True)
    
    # apparently mkisofs modifies the mtime of the file it uses as a boot image.
    # to avoid this, we copy the boot image timestamp and overwrite the original
    # when we finish
    ibin_path = self.cvars['isolinux-dir']/'isolinux.bin'
    ibin_st = ibin_path.stat()
    
    shlib.execute('mkisofs -o %s -b isolinux/isolinux.bin -c isolinux/boot.cat '
                  '-no-emul-boot -boot-load-size 4 -boot-info-table -RJTV "%s" %s' \
                  % (self.bootiso, self.product, isodir))
    ibin_path.utime((ibin_st.st_atime, ibin_st.st_mtime))
    isodir.rm(recursive=True)
    
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    if not self.bootiso.exists():
      raise RuntimeError, "Unable to find boot.iso at '%s'" % self.bootiso

EVENTS = {'INSTALLER': [BootisoEvent]}
