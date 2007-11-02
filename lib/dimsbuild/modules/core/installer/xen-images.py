from dimsbuild.event   import Event

from dimsbuild.modules.shared import FileDownloadMixin, ImageModifyMixin

API_VERSION = 5.0
EVENTS = {'installer': ['XenImagesEvent']}

class XenImagesEvent(Event, ImageModifyMixin, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'xen-images',
      provides = ['vmlinuz-xen', 'initrd-xen'],
      requires = ['anaconda-version', 'buildstamp-file', 'base-repoid'],
      conditionally_requires = ['initrd-image-content', 'kickstart-file', 'ks-path'],
    )

    self.xen_dir = self.SOFTWARE_STORE/'images/xen'

    self.DATA = {
      'config':    ['/distro/initrd-image'],
      'variables': ['cvars[\'anaconda-version\']', 'cvars[\'kickstart-file\']'],
      'input':     [],
      'output':    [],
    }

    ImageModifyMixin.__init__(self, 'initrd.img')
    FileDownloadMixin.__init__(self)

  def error(self, e):
    Event.error(self, e)
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

    # add input files from initrd.img
    self.io.setup_sync(self.imagedir,
                       xpaths='/distro/initrd-image/path',
                       id='%s-input-files' % self.name)

  def run(self):
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
    
    # copy kickstart
    if self.cvars['kickstart-file'] and self.cvars['ks-path']:
      self.image.write(self.cvars['kickstart-file'], self.cvars['ks-path'].dirname)
