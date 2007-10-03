from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared.installer import FileDownloadMixin, ImageModifyMixin

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
      requires = ['anaconda-version', 'buildstamp-file', 'base-repoid'],
      conditionally_requires = ['initrd-image-content'],
    )
    
    self.xen_dir = self.SOFTWARE_STORE/'images/xen'
    
    self.DATA = {
      'config':    ['/distro/initrd-image/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'initrd.img')
    FileDownloadMixin.__init__(self)
  
  def error(self, e):
    try:
      self._close()
    except:
      pass
  
  def setup(self):
    # fool ImageModifyMixin into using the content of initrd.img for xen's
    # initrd.img as well
    self.cvars['xen-images-content'] = self.cvars['initrd-image-content']
    
    self.DATA['input'].append(self.cvars['buildstamp-file'])
    self.diff.setup(self.DATA)
    
    self.image_locals = self.locals.files['xen']['initrd-xen']
    ImageModifyMixin.setup(self)
    self.file_locals = self.locals.files['xen']
    FileDownloadMixin.setup(self)
  
  def run(self):
    self.log(0, L0("preparing xen images"))
    self.io.clean_eventcache(all=True)
    self._download()
    self._modify()
  
  def apply(self):
    self.io.clean_eventcache()
    for file in self.io.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' in '%s'" % (file.basename, file.dirname))
  
  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()


EVENTS = {'INSTALLER': [XenImagesEvent]}
