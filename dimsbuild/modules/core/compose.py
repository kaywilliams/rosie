import csv

from dims.pps.constants import TYPE_NOT_DIR

from dimsbuild.event    import Event
from dimsbuild.logging  import L1

API_VERSION = 5.0
EVENTS = {'OS': ['ComposeEvent']}

FIELDS = ['file', 'size', 'mtime']

class ComposeEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'compose',

      # as an optimization iso diffs 'manifest-file' to determine if it should 
      # run, thus avoiding calculating diffs for all files in SOFTWARE_STORE
      provides = ['os-dir', 'publish-content', 'manifest-file'],
      requires = ['os-content'],
    )

    # put manifest in SOFTWARE_STORE for use by downstream tools, e.g. installer
    self.mfile = self.SOFTWARE_STORE / '.manifest'

    self.DATA =  {
      'variables': ['mfile'],
      'input':     [],
      'output':    [self.mfile],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.events = []
    for event in self._getroot():
      if event.id != self.id:
        event_output_dir = self.METADATA_DIR/event.id/'output/os'
        if event_output_dir.exists():
          self.events.append(event.id)
          for path in event_output_dir.listdir(all=True):
            self.io.setup_sync(self.SOFTWARE_STORE, paths=path, id=event.id)

  def run(self):
    # create composed tree
    self.log(1, L1("linking files"))
    for event in self.events:
      self.io.sync_input(link=True, what=event,
                         text=None)

    # create manifest file
    self.log(1, L1("creating manifest file"))

    manifest = []
    for i in (self.SOFTWARE_STORE).findpaths(nglob=self.mfile,
                                             type=TYPE_NOT_DIR):
      st = i.stat()
      manifest.append({
        'file':  i.relpathfrom(self.SOFTWARE_STORE),
        'size':  st.st_size,
        'mtime': st.st_mtime})
    manifest.sort()

    self.mfile.touch()
    mf = self.mfile.open('w')

    mwriter = csv.DictWriter(mf, FIELDS, lineterminator='\n')
    for line in manifest:
      mwriter.writerow(line)

    mf.close()

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['os-dir'] = self.SOFTWARE_STORE
    self.cvars['manifest-file'] = self.mfile
    self.cvars.setdefault('publish-content', set()).add(self.SOFTWARE_STORE)

  def verify_manifest_exists(self):
    "manifest file exists"
    self.verifier.failUnlessExists(self.mfile)

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnless(self.cvars['os-dir'])
    self.verifier.failUnless(self.cvars['manifest-file'])
