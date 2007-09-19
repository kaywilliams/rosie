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
      'config':    ['/distro/initrd-image/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'initrd.img')
    FileDownloadMixin.__init__(self, self.getBaseRepoId())
  
  def validate(self):
    self.validator.validate('/distro/initrd-image', 'xen.rng')
  
  def error(self, e):
    try:
      self._close()
    except:
      pass
  
  def setup(self):
    ImageModifyMixin.setup(self)
    self._register_image_locals(L_IMAGES)
    self._register_file_locals(L_FILES)
    self.DATA['input'].append(self.cvars['buildstamp-file'])
    
  def run(self):
    self.log(0, "preparing xen images")
    self.remove_output(all=True)
    self._download()
    self._modify()
  
  def apply(self):
    for file in self.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' in '%s'" % (file.basename, file.dirname))
  
  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()


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
