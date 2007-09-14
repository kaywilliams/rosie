from dims import filereader

from dimsbuild.event import Event
from dimsbuild.misc  import locals_imerge

from dimsbuild.modules.installer.lib import ImageModifyMixin

API_VERSION = 5.0

class DiskbootImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'diskboot-image',
      provides = ['diskboot.img'],
      requires = ['initrd-file', 'buildstamp-file'],
      conditionally_requires = ['installer-splash',],
    )
     
    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'config':    ['/distro/installer/diskboot.img'],
      'input':     [],
      'output':    [],
    }
    
    self.mdfile = self.get_mdfile()
    
    ImageModifyMixin.__init__(self, 'diskboot.img')
  
  def _error(self, e):
    try:
      self.close()
    except:
      pass
  
  def _setup(self):
    ImageModifyMixin._setup(self)
    self.register_image_locals(L_IMAGES)

    self.DATA['input'].extend([
      self.cvars['installer-splash'],
      self.cvars['initrd-file'],        
    ])

  def _clean(self):
    self.log(0, "cleaning diskboot-image event")
    self.remove_output(all=True)
    self.clean_metadata()
  
  def _check(self):
    return self.test_diffs()
  
  def _run(self):
    self.log(0, "preparing diskboot image")
    self.remove_output(all=True)
    self.modify()
  
  def _apply(self):
    for file in self.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))

  def generate(self):
    ImageModifyMixin.generate(self)
    self.image.write(self.cvars['installer-splash'], '/')
    self.image.write(self.cvars['initrd-file'], '/')
    bootargs = self.config.get('/distro/installer/diskboot.img/boot-args/text()', None)
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

#------ LOCALS ------#
L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="diskboot.img">
        <format>fat32</format>
        <path>images</path>
      </image>
    </images>
  </images-entries>
</locals>
'''
