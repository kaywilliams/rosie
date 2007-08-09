from os.path import join, exists

from dims import osutils

from dimsbuild.event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'xen-images',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['vmlinuz-xen', 'initrd-xen'],
    'requires': ['anaconda-version', 'initrd-file', 'buildstamp-file'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'XenHook':      'xen-images',
  'ValidateHook': 'validate',
}

XEN_OUTPUT_FILES = [
  'images/xen/initrd.img',
  'images/xen/vmlinuz',
]

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.xen.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/installer/initrd.img', 'xen.rng')
    
class XenHook(ImageModifyMixin, FileDownloadMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.xen.xen-images'
    
    self.interface = interface

    self.xen_dir = join(self.interface.SOFTWARE_STORE, 'images/xen')

    self.DATA = {
      'config':    ['/distro/installer/initrd.img/path/text()'],
      'variables': ['interface.cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [ join(interface.SOFTWARE_STORE, x) for x in XEN_OUTPUT_FILES ],
    }
  
    ImageModifyMixin.__init__(self, 'initrd.img', interface, self.DATA,
                           mdfile=join(interface.METADATA_DIR, 'initrd.img-xen.md'))
    FileDownloadMixin.__init__(self, interface, self.interface.getBaseRepoId())
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def setup(self):
    ImageModifyMixin.setup(self)
    self.register_image_locals(L_IMAGES)
    self.register_file_locals(L_FILES)
    self.update({
      'input': self.interface.cvars['buildstamp-file'],
    })
    
  def clean(self):
    self.remove_files([ join(self.interface.SOFTWARE_STORE, x) for x in XEN_OUTPUT_FILES ])
  
  def check(self):
    return not self.validate_image() or \
           self.test_diffs()
  
  def run(self):
    self.interface.log(0, "preparing xen images")
    osutils.mkdir(self.xen_dir, parent=True)
    
    # clean up old output
    self.clean()
    # download files
    self.download() # see FileDownloadMixin.download() in lib.py
    # modify initrd.img
    self.modify() # see ImageModifyMixin.modify() in lib.py
  
  def apply(self):
    for file in XEN_OUTPUT_FILES:
      if not exists(join(self.interface.SOFTWARE_STORE, file)):
        raise RuntimeError, "Unable to find '%s' in '%s'" % (file, join(self.interface.SOFTWARE_STORE, file))

  def generate(self):
    ImageModifyMixin.generate(self)
    self.write_buildstamp()
  

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
