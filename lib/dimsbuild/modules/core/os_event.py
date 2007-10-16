from dims.dispatch import PROPERTY_META

import csv

from dims.pps.constants import TYPE_NOT_DIR

from dimsbuild.event    import Event
from dimsbuild.logging  import L0, L1

API_VERSION = 5.0

FIELDS = ['file', 'size', 'mtime']

class OSMetaEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'OS',
      properties = PROPERTY_META,
      comes_after = ['setup'],
    )

class OSComposeEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'os-compose',
      provides = ['os-dir', 'publish-content', '.manifest'],
      requires = ['os-content'],
    )

    self.osdir = self.mddir / 'output/os'

    # put manifest in osdir for use by downstream tools, e.g. installer
    self.mfile = self.osdir / '.manifest'

    self.DATA =  {
      'variables': ['osdir', 'mfile'],
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
            self.io.setup_sync(self.osdir, paths=path, id=event.id)

  def run(self):
    self.log(0, L0("composing os tree"))

    # create composed tree
    self.log(1, L1("linking files"))
    backup = self.files_callback.sync_start
    self.files_callback.sync_start = lambda : None
    for event in self.events:
      self.io.sync_input(copy=True, link=True, what=event)
    self.files_callback.sync_start = backup

    # create manifest file
    self.log(1, L1("creating manifest file"))

    manifest = []
    for i in (self.SOFTWARE_STORE).findpaths(nglob=self.mfile,
                                             type=TYPE_NOT_DIR):
      st = i.stat()
      manifest.append({
        'file':  i[len(self.SOFTWARE_STORE)+1:],
        'size':  st.st_size,
        'mtime': st.st_mtime,})
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
    self.cvars['os-dir'] = self.osdir
    try:
      self.cvars['publish-content'].add(self.osdir)
    except:
      pass

EVENTS = {'ALL': [OSMetaEvent], 'OS': [OSComposeEvent]}
