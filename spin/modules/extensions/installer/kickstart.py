from rendition import pps

from spin.event   import Event

API_VERSION = '5.0'
EVENTS = {'installer': ['KickstartEvent']}

class KickstartEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'kickstart',
      version = 1,
      provides = ['kickstart-file', 'ks-path', 'initrd-image-content'],
    )

    self.DATA = {
      'config': ['.'],
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.io.setup_sync(self.SOFTWARE_STORE, id='kickstart-file', xpaths=['.'])

  def run(self):
    self.io.sync_input(cache=True)
    self.diff.write_metadata()

  def apply(self):
    self.cvars['kickstart-file'] = self.io.list_output(what='kickstart-file')[0]
    self.cvars['ks-path'] = pps.Path('/%s' % self.cvars['kickstart-file'].basename)

  def verify_cvars(self):
    "cvars are set"
    self.verifier.failUnless(self.cvars['ks-path'])
