from dims import filereader

from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared.installer import FileDownloadMixin

API_VERSION = 5.0

class IsolinuxEvent(Event, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'isolinux',
      provides = ['isolinux-files'],
      requires = ['anaconda-version', 'source-vars', 'base-repoid'],
    )

    self.isolinux_dir = self.SOFTWARE_STORE/'isolinux' #! not versioned

    self.DATA = {
      'config':    ['/distro/isolinux'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }

    FileDownloadMixin.__init__(self)

  def validate(self):
    self.validator.validate('/distro/isolinux', 'isolinux.rng')

  def setup(self):
    self.diff.setup(self.DATA)
    self.file_locals = self.locals.files['isolinux']
    FileDownloadMixin.setup(self)

  def run(self):
    self.log(0, L0("synchronizing isolinux files"))
    self._download()

    # modify the first append line in isolinux.cfg
    bootargs = self.config.get('/distro/isolinux/boot-args/text()', None)
    if bootargs:
      cfg = self.SOFTWARE_STORE/self.file_locals['isolinux.cfg']['path']
      if not cfg.exists():
        raise RuntimeError("missing file '%s'" % cfg)
      lines = filereader.read(cfg)

      for i, line in enumerate(lines):
        if line.strip().startswith('append'):
          break
      value = lines.pop(i)
      value = value.strip() + ' %s' % bootargs.strip()
      lines.insert(i, value)
      filereader.write(lines, cfg)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    for file in self.io.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s'" % file)
    
    self.cvars['isolinux-files'] = {}
    for k,v in self.file_locals.items():
      self.cvars['isolinux-files'][k] = self.SOFTWARE_STORE/v['path']

EVENTS = {'INSTALLER': [IsolinuxEvent]}
