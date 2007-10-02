import os

from dims import filereader

from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared.installer import FileDownloadMixin, ImageModifyMixin

API_VERSION = 5.0

class IsolinuxEvent(Event, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'isolinux',
      provides = ['vmlinuz-file', 'isolinux-dir'],
      requires = ['anaconda-version', 'source-vars', 'base-repoid'],
    )
    
    self.isolinux_dir = self.SOFTWARE_STORE/'isolinux' #! not versioned
    
    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
      'config':    ['/distro/isolinux'],
    }
    
    FileDownloadMixin.__init__(self)

  def validate(self):
    self.validator.validate('/distro/isolinux', 'isolinux.rng')
    
  def setup(self):
    self.diff.setup(self.DATA)
    self.file_locals = self.locals.files['isolinux']
    FileDownloadMixin.setup(self)
    self.io.setup_sync(self.isolinux_dir, id='IsoLinuxFiles',
                    xpaths=['/distro/isolinux/path'])
  
  def run(self):
    self.log(0, L0("synchronizing isolinux files"))
    self._download()
    self.io.sync_input(what='IsoLinuxFiles')
    
    # modify the first append line in isolinux.cfg
    bootargs = self.config.get('/distro/isolinux/boot-args/text()', None)
    if bootargs:
      cfg = self.isolinux_dir/'isolinux.cfg'
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
    # fix this, this must be doable via list_output
    self.cvars['isolinux-dir'] = self.isolinux_dir
    self.cvars['vmlinuz-file'] = \
      self.SOFTWARE_STORE/self.file_locals['vmlinuz']['path']


class InitrdImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'initrd-image',
      provides = ['initrd-file'],
      requires = ['anaconda-version', 'buildstamp-file'],
      comes_before = ['isolinux'],
    )
    
    self.DATA = {
      'config':    ['/distro/initrd-image/path'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [] # to be filled later
    }
    
    ImageModifyMixin.__init__(self, 'initrd.img')
  
  def error(self, e):
    try:
      self._close()
    except:
      pass
  
  def setup(self):
    self.diff.setup(self.DATA)
    self.image_locals = self.locals.files['isolinux']['initrd.img']
    ImageModifyMixin.setup(self)
  
  def run(self):
    self.log(0, L0("preparing initrd.img"))
    self.io.clean_eventcache(all=True)
    self._modify()
  
  def apply(self):
    self.io.clean_eventcache()
    for file in self.io.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))
    # fix this, this must be doable via io.list_output
    self.cvars['initrd-file'] = \
      self.SOFTWARE_STORE/self.image_locals['path']
  
  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()


EVENTS = {'INSTALLER': [IsolinuxEvent, InitrdImageEvent]}
