from dimsbuild.event   import Event
from dimsbuild.logging import L0

API_VERSION = 5.0


class PxebootImagesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pxeboot-images',
      provides = ['pxeboot'],
      requires = ['isolinux-files'],
    )

    self.DATA = {
      'input':  [],
      'output': [],
    }
    
    self.pxebootdir = self.SOFTWARE_STORE/'images/pxeboot'
  
  def setup(self):
    self.diff.setup(self.DATA)
    paths = [self.cvars['isolinux-files']['vmlinuz'],
             self.cvars['isolinux-files']['initrd.img']]
    self.io.setup_sync(self.pxebootdir, paths=paths)
    
  def run(self):
    self.log(0, L0("preparing pxeboot images"))
    self.io.sync_input(cache=True)
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    for file in ['vmlinuz', 'initrd.img']:
      if not (self.pxebootdir/file).exists():
        raise RuntimeError("Unable to find '%s' in '%s'" % (file, self.pxebootdir))


EVENTS = {'installer': [PxebootImagesEvent]}
