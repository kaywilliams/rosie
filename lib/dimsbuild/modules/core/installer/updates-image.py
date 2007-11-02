from dimsbuild.event   import Event

from dimsbuild.modules.shared import ImageModifyMixin

API_VERSION = 5.0
EVENTS = {'installer': ['UpdatesImageEvent']}

class UpdatesImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'updates-image',
      provides = ['updates.img'],
      requires = ['buildstamp-file', 'anaconda-version', 'base-repoid'],
      conditionally_requires = ['updates-image-content'],
    )
    
    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'updates.img')
  
  def error(self, e):
    try:
      self._close()
    except:
      pass
    Event.error(self, e)
  
  def setup(self):
    self.image_locals = self.locals.files['installer']['updates.img']
    ImageModifyMixin.setup(self)
  
  def run(self):
    self._modify()
