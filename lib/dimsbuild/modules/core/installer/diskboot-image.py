from StringIO import StringIO

from dims import pps

from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared import ImageModifyMixin, BootConfigMixin

P = pps.Path

API_VERSION = 5.0
EVENTS = {'installer': ['DiskbootImageEvent']}

class DiskbootImageEvent(Event, ImageModifyMixin, BootConfigMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'diskboot-image',
      provides = ['diskboot.img'],
      requires = ['buildstamp-file', 'base-repoid', 'installer-splash',
                  'boot-config-file'], #! check installer-splash
      conditionally_requires = ['diskboot-image-content', 'web-path',
                                'boot-args', 'ks-path'],
    )
     
    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']', 'cvars[\'ks-path\']'],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'diskboot.img')
    BootConfigMixin.__init__(self)

  def error(self, e):
    try:
      self._close()
    except:
      pass
    Event.error(self, e)
  
  def setup(self):
    self.DATA['input'].extend([
      self.cvars['installer-splash'],
      self.cvars['isolinux-files']['initrd.img'],
    ])
    
    self.image_locals = self.locals.files['installer']['diskboot.img']
    boot_arg_defaults = 'nousbstorage'
    if self.cvars['web-path']:
      boot_arg_defaults += ' method=%s/os' % self.cvars['web-path']
    if self.cvars['ks-path']:
      boot_arg_defaults += ' ks=file:%s' % self.cvars['ks-path']
    self.bootconfig.setup(defaults=boot_arg_defaults)
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
    
    # hack to modify boot args in syslinux.cfg file
    for file in self.image.list():
      if file.basename == 'syslinux.cfg':
        self.bootconfig.modify(file); break
