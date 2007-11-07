from dimsbuild.event   import Event

API_VERSION = 5.0
EVENTS = {'installer': ['PxebootImagesEvent']}

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
    self.io.sync_input(cache=True)
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()

  def verify_output_exists(self):
    "verify all output exists"
    for file in ['vmlinuz', 'initrd.img']:
      self.verifier.failUnless((self.pxebootdir/file).exists(),
        "unable to find %s at '%s'" % (file, self.pxebootdir/file))
