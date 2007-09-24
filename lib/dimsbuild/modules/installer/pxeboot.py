from dimsbuild.event   import Event
from dimsbuild.logging import L0

API_VERSION = 5.0


class PxebootImagesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pxeboot-images',
      provides = ['pxeboot'],
      requires = ['vmlinuz-file', 'initrd-file'],
    )

    self.DATA = {
      'input':  [],
      'output': [],      
    }
    
    self.pxebootdir = self.SOFTWARE_STORE/'images/pxeboot'
  
  def setup(self):
    self.diff.setup(self.DATA)
    paths = [self.cvars['vmlinuz-file'], self.cvars['initrd-file']]
    self.io.setup_sync(self.pxebootdir, paths=paths)
    
  def run(self):
    self.log(0, L0("preparing pxeboot images"))
    self.io.remove_output()
    self.io.sync_input()
    self.diff.write_metadata()
  
  def apply(self):
    for file in ['vmlinuz', 'initrd.img']:
      if not (self.pxebootdir/file).exists():
        raise RuntimeError("Unable to find '%s' in '%s'" % (file, self.pxebootdir))


EVENTS = {'INSTALLER': [PxebootImagesEvent]}
