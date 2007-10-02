from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared.installer import FileDownloadMixin

API_VERSION = 5.0

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
    self.log(0, L0("synchronizing stage2 images"))
    self._download()
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    for file in self.io.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find file '%s' at '%s'" % (file.basename, file.dirname))


EVENTS = {'INSTALLER': [Stage2ImagesEvent]}
