import os

from os.path import join, exists

from dims import filereader
from dims import osutils
from dims import sync

from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 4.1

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'isolinux',
    'provides': ['vmlinuz', 'isolinux-changed'],
    'requires': ['anaconda-version', 'source-vars', 'initrd-file'], #! 'initrd-file' for run-before functionality
    'parent': 'INSTALLER',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
  {
    'id': 'initrd-image',
    'provides': ['initrd-file', 'isolinux-changed'],
    'requires': ['anaconda-version', 'buildstamp-file'],
    #'run-before': ['isolinux'],
    'parent': 'INSTALLER',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'IsolinuxHook': 'isolinux',
  'InitrdHook':   'initrd-image',
}


#------ HOOKS ------#
class IsolinuxHook(FileDownloadMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.isolinux'
    
    self.interface = interface
    
    self.isolinux_dir = join(self.interface.SOFTWARE_STORE, 'isolinux') #! not versioned

    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
      'config':    ['/distro/installer/isolinux'],
    }
    
    self.mdfile = join(self.interface.METADATA_DIR, 'INSTALLER', 'isolinux.md')
    FileDownloadMixin.__init__(self, interface, self.interface.getBaseRepoId())
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    self.register_file_locals(L_FILES)
    o = self.interface.setup_sync(xpaths=[('/distro/installer/isolinux/path',
                                           self.isolinux_dir)],
                                  id='IsoLinuxFiles')
    self.DATA['output'].extend(o)

  def clean(self):
    self.interface.log(0, "cleaning isolinux event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
    
  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "synchronizing isolinux files")
    self.interface.remove_output()
    self.download()
    self.interface.sync_input(what='IsoLinuxFiles')
    
    # modify the first append line in isolinux.cfg
    bootargs = self.interface.config.get('/distro/installer/isolinux/boot-args/text()', None)
    if bootargs:
      cfg = join(self.isolinux_dir, 'isolinux.cfg')
      if not exists(cfg):
        raise RuntimeError("missing file '%s'" % cfg)
      lines = filereader.read(cfg)
      
      for i, line in enumerate(lines):
        if line.strip().startswith('append'):
          break
      value = lines.pop(i)
      value = value.strip() + ' %s' % bootargs.strip()
      lines.insert(i, value)
      filereader.write(lines, cfg)
    
    self.interface.cvars['isolinux-changed'] = True
      
  def apply(self):
    self.interface.write_metadata()
    for file in self.interface.list_output():
      if not exists(file):
        raise RuntimeError("Unable to find '%s'" % file)
    
class InitrdHook(ImageModifyMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.initrd'
    
    self.interface = interface
    
    self.DATA = {
      'config':    ['/distro/installer/initrd.img/path'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [] # to be filled later
    }
    
    ImageModifyMixin.__init__(self, 'initrd.img', interface, self.DATA)
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def setup(self):
    ImageModifyMixin.setup(self)
    self.register_image_locals(L_IMAGES)

  def clean(self):
    self.interface.log(0, "cleaning initrd-image event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
  
  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "processing initrd.img")
    self.interface.remove_output(all=True)
    self.modify()    
    self.interface.cvars['isolinux-changed'] = True
  
  def apply(self):
    for file in self.interface.list_output():
      if not exists(join(self.interface.SOFTWARE_STORE, file)):
        raise RuntimeError("Unable to find '%s' at '%s'"  \
                           % (file, join(self.interface.SOFTWARE_STORE)))
    initrd = self.i_locals.get('//image[@id="initrd.img"]')
    self.interface.cvars['initrd-file'] = join(self.interface.SOFTWARE_STORE,
                                               initrd.get('path/text()'), 'initrd.img')

  def generate(self):
    ImageModifyMixin.generate(self)
    self.write_buildstamp()

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
