from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.installer.lib import ImageModifyMixin

API_VERSION = 5.0

class UpdatesImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'updates-image',
      provides = ['updates.img'],
      requires = ['buildstamp-file', 'anaconda-version'],
      conditionally_comes_after = ['installer-logos'],
    )
    
    self.DATA = {
      'config':    ['/distro/installer/updates-image/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'updates.img')
  
  def validate(self):
    self.validator.validate('/distro/installer/updates-image', 'updates.rng')
  
  def error(self, e):
    try:
      self._close()
    except:
      pass
  
  def setup(self):
    self.image_locals = self.locals.files['installer']['updates.img']
    ImageModifyMixin.setup(self)
  
  def run(self):
    self.log(0, L0("generating updates.img"))
    self._modify()
    
  def apply(self):
    self.io.clean_eventcache()
    for file in self.io.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))


EVENTS = {'INSTALLER': [UpdatesImageEvent]}
