from dimsbuild.event import Event

from dimsbuild.modules.installer.lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 5.0

XEN_OUTPUT_FILES = [
  'images/xen/initrd.img',
  'images/xen/vmlinuz',
]

class XenImagesEvent(Event, ImageModifyMixin, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'xen-images',
      provides = ['vmlinuz-xen', 'initrd-xen'],
      requires = ['anaconda-version', 'initrd-file', 'buildstamp-file'],
    )
    
    self.xen_dir = self.SOFTWARE_STORE/'images/xen'
    
    self.DATA = {
      'config':    ['/distro/installer/initrd.img/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'initrd.img')
    FileDownloadMixin.__init__(self, self.getBaseRepoId())
  
  def _validate(self):
    self.validate('/distro/installer/initrd.img', 'xen.rng')
  
  def _error(self, e):
    try:
      self.close()
    except:
      pass
  
  def _setup(self):
    ImageModifyMixin._setup(self)
    self.register_image_locals(L_IMAGES)
    self.register_file_locals(L_FILES)
    self.DATA['input'].append(self.cvars['buildstamp-file'])
    
  def _run(self):
    self.log(0, "preparing xen images")
    self.remove_output(all=True)
    self.download()
    self.modify()
  
  def _apply(self):
    for file in self.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' in '%s'" % (file.basename, file.dirname))
  
  def generate(self):
    ImageModifyMixin.generate(self)
    self.write_buildstamp()


EVENTS = {'INSTALLER': [XenImagesEvent]}

L_FILES = ''' 
<locals>
  <files-entries>
    <files version="0">
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
