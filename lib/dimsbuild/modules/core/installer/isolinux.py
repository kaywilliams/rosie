from dimsbuild.event   import Event

from dimsbuild.modules.shared import FileDownloadMixin

API_VERSION = 5.0
EVENTS = {'installer': ['IsolinuxEvent']}

class IsolinuxEvent(Event, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'isolinux',
      provides = ['isolinux-files', 'boot-config-file'],
      requires = ['anaconda-version', 'source-vars', 'base-repoid'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }

    FileDownloadMixin.__init__(self)
  
  def setup(self):
    self.diff.setup(self.DATA)
    self.file_locals = self.locals.files['isolinux']
    FileDownloadMixin.setup(self)
  
  def run(self):
    self._download()
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    
    self.cvars['isolinux-files'] = {}
    for k,v in self.file_locals.items():
      self.cvars['isolinux-files'][k] = self.SOFTWARE_STORE/v['path']
    
    self.cvars['boot-config-file'] = \
      self.SOFTWARE_STORE/self.file_locals['isolinux.cfg']['path']
