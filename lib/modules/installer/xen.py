from os.path import join, exists

from dims import osutils

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from installer.lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'xen-images',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['vmlinuz-xen', 'initrd-xen'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'XenHook': 'xen-images',
}

XEN_OUTPUT_FILES = [
  'images/xen/initrd.img',
  'images/xen/vmlinuz',
]

#------ HOOKS ------#
class XenHook(ImageModifyMixin, FileDownloadMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.xen.xen-images'
    
    self.interface = interface

    self.xen_dir = join(self.interface.SOFTWARE_STORE, 'images/xen')

    xen_md_struct = {
      'config':    ['/distro/main/product/text()',
                    '/distro/main/version/text()',
                    '/distro/main/fullname/text()',
                    '/distro/installer/initrd.img/path/text()'],
      'variables': ['anaconda_version'],
      'input':     [interface.config.mget('/distro/installer/initrd.img/path/text()', [])],
      'output':    [join(interface.SOFTWARE_STORE, x) for x in XEN_OUTPUT_FILES ],
    }
  
    ImageModifyMixin.__init__(self, 'initrd.img', interface, xen_md_struct,
                           mdfile=join(interface.METADATA_DIR, 'initrd.img-xen.md'))
    FileDownloadMixin.__init__(self, interface)
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def force(self):
    osutils.rm(self.xen_dir, recursive=True, force=True)
  
  def run(self):
    self.register_image_locals(L_IMAGES)
    self.register_file_locals(L_FILES)
    
    if not self._test_runstatus(): return
    
    self.interface.log(0, "preparing xen images")
    i,_,_,d,_,_ = self.interface.getStoreInfo(self.interface.getBaseStore())
    
    osutils.mkdir(self.xen_dir, parent=True)
    
    # download files
    self.download(d,i) # see FileDownloadMixin.download() in lib.py
    
    # modify initrd.img
    self.modify() # see ImageModifyMixin.modify() in lib.py
  
  def apply(self):
    for file in XEN_OUTPUT_FILES:
      if not exists(join(self.interface.SOFTWARE_STORE, file)):
        raise RuntimeError, "Unable to find '%s' in '%s'" % (file, join(self.interface.SOFTWARE_STORE, file))
  
  def _test_runstatus(self):
    return self.interface.isForced('xen-images') or \
           self.check_run_status()


L_FILES = ''' 
<locals>
  <files-entries>
    <files version="0">
      <file id="initrd.img">
        <path>images/xen</path>
      </file>
      <file id="vmlinuz">
        <path>images/xen</path>
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
        <path>images/xen</path>
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
