from dims import filereader

from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared.installer import ImageModifyMixin


API_VERSION = 5.0


class DiskbootImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'diskboot-image',
      provides = ['diskboot.img'],
      requires = ['buildstamp-file', 'base-repoid', 'installer-splash'], #! check installer-splash
      conditionally_requires = ['diskboot-image-content'],
    )
     
    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'config':    ['/distro/diskboot-image'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'diskboot.img')

  def validate(self):
    self.validator.validate('/distro/diskboot-image', 'diskboot.rng')
  
  def error(self, e):
    Event.error(e)
    try:
      self._close()
    except:
      pass
  
  def setup(self):
    self.DATA['input'].extend([
      self.cvars['installer-splash'],
      self.cvars['isolinux-files']['initrd.img'],
    ])
    
    self.image_locals = self.locals.files['installer']['diskboot.img']
    ImageModifyMixin.setup(self)
    
  def run(self):
    self.log(0, L0("preparing diskboot image"))
    self.io.clean_eventcache(all=True)
    self._modify()
  
  def apply(self):
    self.io.clean_eventcache()
    for file in self.io.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))
  
  def _generate(self):
    ImageModifyMixin._generate(self)
    self.image.write(self.cvars['installer-splash'], '/')
    self.image.write(self.cvars['isolinux-files']['initrd.img'], '/')
    bootargs = self.config.get('/distro/diskboot-image/boot-args/text()', None)
    if bootargs:
      if not 'syslinux.cfg' in self.image.list():
        raise RuntimeError("syslinux.cfg not found in the diskboot.img")
      wcopy = self.TEMP_DIR/'syslinux.cfg'
      if wcopy.exists():
        wcopy.remove()
      
      self.image.read('syslinux.cfg', self.TEMP_DIR)
      lines = filereader.read(wcopy)
      for i, line in enumerate(lines):
        if line.strip().startswith('append'):
          break
      
      value = lines.pop(i)
      value = value.strip() + ' ' + bootargs.strip()
      lines.insert(i, value)
      filereader.write(lines, wcopy)
      self.image.write(wcopy, '/')
      wcopy.remove()

EVENTS = {'INSTALLER': [DiskbootImageEvent]}
