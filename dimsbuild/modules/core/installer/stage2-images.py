from dimsbuild.event   import Event

from dimsbuild.modules.shared import FileDownloadMixin

API_VERSION = 5.0
EVENTS = {'installer': ['Stage2ImagesEvent']}

class Stage2ImagesEvent(Event, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'stage2-images',
      provides = ['stage2'],
      requires = ['anaconda-version', 'source-vars', 'base-repoid'],
    )

    self.DATA = {
      'input':  [],
      'output': [],
    }

    FileDownloadMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.file_locals = self.locals.files['stage2']
    FileDownloadMixin.setup(self)

  def run(self):
    self._download()
    self.diff.write_metadata()
