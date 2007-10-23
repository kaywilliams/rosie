from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared import ImageModifyMixin

API_VERSION = 5.0

class InitrdImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'initrd-image',
      provides = ['isolinux-files'],
      requires = ['anaconda-version', 'buildstamp-file'],
      conditionally_requires = ['initrd-image-content'],
      comes_after = ['isolinux'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
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
    self.log(0, L0("preparing initrd.img"))
    self.io.clean_eventcache(all=True)
    self._modify()

  def apply(self):
    self.io.clean_eventcache()
    for file in self.io.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))
    self.cvars['isolinux-files']['initrd.img'] = self.SOFTWARE_STORE/self.image_locals['path']

  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()


EVENTS = {'installer': [InitrdImageEvent]}
