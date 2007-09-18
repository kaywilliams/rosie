import os

from dims import filereader

from dimsbuild.event import Event

from dimsbuild.modules.installer.lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 5.0

class IsolinuxEvent(Event, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'isolinux',
      provides = ['vmlinuz-file', 'isolinux-files'],
      requires = ['anaconda-version', 'source-vars'],
    )
    
    self.isolinux_dir = self.SOFTWARE_STORE/'isolinux' #! not versioned
    
    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
      'config':    ['/distro/installer/isolinux'],
    }
    
    FileDownloadMixin.__init__(self, self.getBaseRepoId())
  
  def setup(self):
    self.setup_diff(self.DATA)
    self._register_file_locals(L_FILES)
    self.setup_sync(self.isolinux_dir, id='IsoLinuxFiles',
                    xpaths=['/distro/installer/isolinux/path'])
  
  def run(self):
    self.log(0, "synchronizing isolinux files")
    self.remove_output()
    self._download()
    self.sync_input(what='IsoLinuxFiles')
    
    # modify the first append line in isolinux.cfg
    bootargs = self.config.get('/distro/installer/isolinux/boot-args/text()', None)
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
    
    self.write_metadata()
  
  def apply(self):
    for file in self.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s'" % file)
    vmlinuz = self.f_locals.get('//file[@id="vmlinuz"]')
    # fix this, this must be doable via list_output
    self.cvars['vmlinuz-file'] = self.SOFTWARE_STORE / \
                                 vmlinuz.get('path/text()') / \
                                 'vmlinuz'


class InitrdImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'initrd-image',
      provides = ['initrd-file'],
      requires = ['anaconda-version', 'buildstamp-file'],
      comes_before = ['isolinux'],
    )
    
    self.DATA = {
      'config':    ['/distro/installer/initrd.img/path'],
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
    ImageModifyMixin.setup(self)
    self._register_image_locals(L_IMAGES)
  
  def run(self):
    self.log(0, "processing initrd.img")
    self.remove_output(all=True)
    self._modify()
  
  def apply(self):
    for file in self.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))
    initrd = self.i_locals.get('//image[@id="initrd.img"]')
    # fix this, this must be doable via list_output
    self.cvars['initrd-file'] = self.SOFTWARE_STORE / \
                                initrd.get('path/text()') / \
                                'initrd.img'
  
  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()


EVENTS = {'INSTALLER': [IsolinuxEvent, InitrdImageEvent]}

#------ LOCALS ------#
L_FILES = ''' 
<locals>
  <files-entries>
    <files version="0">
      <file id="boot.msg">
        <path>isolinux</path>
      </file>
      <file id="general.msg">
        <path>isolinux</path>
      </file>
      <file id="isolinux.bin">
        <path>isolinux</path>
      </file>
      <file id="isolinux.cfg">
        <path>isolinux</path>
      </file>
      <file id="memtest">
        <path>isolinux</path>
      </file>
      <file id="options.msg">
        <path>isolinux</path>
      </file>
      <file id="param.msg">
        <path>isolinux</path>
      </file>
      <file id="rescue.msg">
        <path>isolinux</path>
      </file>
      <file id="vmlinuz">
        <path>isolinux</path>
      </file>
    </files>
    
    <!-- 11.2.0.66-1 - memtest removed, vesamenu.c32 added -->
    <files version="11.2.0.66-1">
      <action type="delete" path="file[@id='memtest']"/>
      <action type="insert" path=".">
        <file id="vesamenu.c32">
          <path>isolinux</path>
        </file>
      </action>
    </files>
  </files-entries>
</locals>
'''

L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="initrd.img">
        <format>ext2</format>
        <zipped>True</zipped>
        <path>isolinux</path>
      </image>
    </images>
    
    <!-- approx 10.2.0.3-1 - initrd.img format changed to cpio -->
    <images version="10.2.0.3-1">
      <action type="update" path="image[@id='initrd.img']">
        <format>cpio</format>
      </action>
    </images>
  </images-entries>
</locals>
'''
