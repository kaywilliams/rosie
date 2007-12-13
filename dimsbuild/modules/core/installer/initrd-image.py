from dimsbuild.event   import Event

from dimsbuild.modules.shared import ImageModifyMixin

API_VERSION = 5.0
EVENTS = {'installer': ['InitrdImageEvent']}

class InitrdImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'initrd-image',
      provides = ['isolinux-files'],
      requires = ['anaconda-version', 'buildstamp-file'],
      conditionally_requires = ['initrd-image-content', 'kickstart-file', 'ks-path'],
      comes_after = ['isolinux'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']', 'cvars[\'kickstart-file\']'],
      'input':     [],
      'output':    [] # to be filled later
    }

    ImageModifyMixin.__init__(self, 'initrd.img')

  def error(self, e):
    try:
      self._close()
    except:
      pass
    Event.error(self, e)

  def setup(self):
    self.diff.setup(self.DATA)
    self.image_locals = self.locals.files['isolinux']['initrd.img']
    ImageModifyMixin.setup(self)

  def run(self):
    self._modify()

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['isolinux-files']['initrd.img'] = self.SOFTWARE_STORE/self.image_locals['path']

  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()

    # copy kickstart file
    if self.cvars['kickstart-file'] and self.cvars['ks-path']:
      self.image.write(self.cvars['kickstart-file'], self.cvars['ks-path'].dirname)
