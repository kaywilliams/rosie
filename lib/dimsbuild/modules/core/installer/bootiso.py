from dims import shlib

from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared import BootConfigMixin

API_VERSION = 5.0

class BootisoEvent(Event, BootConfigMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'bootiso',
      requires = ['isolinux-files', 'boot-config-file'],
      conditionally_requires = ['installer-splash', 'web-path', 'boot-args',
                                'kickstart-file'],
    )
    
    self.bootiso = self.SOFTWARE_STORE/'images/boot.iso'
    
    self.DATA = {
      'config': ['.'],
      'input':  [],
      'output': [self.bootiso],
    }
    
    BootConfigMixin.__init__(self)
  
  def setup(self):
    self.diff.setup(self.DATA)
    self.DATA['input'].extend(self.cvars['isolinux-files'].values())
    boot_arg_defaults = ''
    if self.cvars['web-path']:
      boot_arg_defaults += ' method=%s/os' % self.cvars['web-path']
    if self.cvars['kickstart-file']: # this one will need adjusting methinks
      boot_arg_defaults += ' ks=file:/%s' % self.cvars['kickstart-file']
    self.bootconfig.setup(defaults=boot_arg_defaults)
  
  def run(self):
    self.log(0, L0("generating boot.iso"))
    
    isodir = self.SOFTWARE_STORE/'images/isopath'
    isolinuxdir = isodir/'isolinux'
    
    isolinuxdir.mkdirs()
    for file in self.cvars['isolinux-files'].values():
      self.link(file, isolinuxdir)
    
    # modify isolinux.cfg
    self.bootconfig.modify(
      isodir/self.locals.files['isolinux']['isolinux.cfg']['path'])
    
    # apparently mkisofs modifies the mtime of the file it uses as a boot image.
    # to avoid this, we copy the boot image timestamp and overwrite the original
    # when we finish
    ibin_st = self.cvars['isolinux-files']['isolinux.bin'].stat()
    shlib.execute('mkisofs -o %s -b isolinux/isolinux.bin -c isolinux/boot.cat '
                  '-no-emul-boot -boot-load-size 4 -boot-info-table -RJTV "%s" %s' \
                  % (self.bootiso, self.product, isodir))
    self.cvars['isolinux-files']['isolinux.bin'].utime((ibin_st.st_atime, ibin_st.st_mtime))
    isodir.rm(recursive=True)
    
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    if not self.bootiso.exists():
      raise RuntimeError, "Unable to find boot.iso at '%s'" % self.bootiso

EVENTS = {'installer': [BootisoEvent]}
