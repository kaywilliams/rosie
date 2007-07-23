import os

from os.path import join, exists

from dims import filereader
from dims import osutils
from dims import sync

from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import DiffMixin, FilesMixin

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
class IsolinuxHook(FileDownloadMixin, FilesMixin, DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.isolinux'
    
    self.interface = interface
    
    self.isolinux_dir = join(self.interface.SOFTWARE_STORE, 'isolinux') #! not versioned

    self.DATA = {
      'variables': ['interface.cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
      'config':    ['/distro/installer/isolinux'],
    }
    
    self.mdfile = join(self.interface.METADATA_DIR, 'isolinux.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
    FileDownloadMixin.__init__(self, interface, self.interface.getBaseRepoId())
    FilesMixin.__init__(self, self.isolinux_dir)
  
  def setup(self):
    repo = self.interface.getRepo(self.interface.getBaseRepoId())
    self.register_file_locals(L_FILES)

    self.add_files('/distro/installer/isolinux/path')
    
    self.update({
      'input': [ repo.rjoin(f.get('path/text()'),
                            f.get('@id')) \
                 for f in self.f_locals.xpath('//file') ],
      'output': [ join(self.interface.SOFTWARE_STORE,
                       f.get('path/text()'),
                       f.get('@id')) \
                  for f in self.f_locals.xpath('//file') ],
    })

  def force(self):
    self.interface.log(0, "forcing isolinux")
    self.remove_files(self.handlers['output'].oldoutput.keys())
  
  def check(self):
    if self.test_diffs():
      if not self.interface.isForced('isolinux'):
        self.interface.log(0, "cleaning isolinux")
        self.remove_files(self.handlers['output'].oldoutput.keys())
      return True
    else:    
      return False
  
  def run(self):
    self.interface.log(0, "synchronizing isolinux files")    
    osutils.mkdir(self.isolinux_dir, parent=True)

    # download all files - see FileDownloadMixin.download() in lib.py    
    self.download()

    # copy input files - see FilesMixin.sync_files() in interface.py
    self.sync_files('/distro/installer/isolinux/path')
    
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

    self.write_metadata()    
  
  def apply(self):
    for file in self.DATA['output']:
      if not exists(file):
        raise RuntimeError, "Unable to find '%s'" % file
    
class InitrdHook(ImageModifyMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.initrd'
    
    self.interface = interface
    
    self.DATA = {
      'config':    ['/distro/installer/initrd.img/path'],
      'variables': ['interface.cvars[\'anaconda-version\']'],
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

    repo = self.interface.getRepo(self.interface.getBaseRepoId())

    # add input files
    self.update({
      'input':  [
        [ join(self.interface.INPUT_STORE,
               repo.id, repo.directory,
               f.get('path/text()'),
               f.get('@id')) \
          for f in self.i_locals.xpath('//image') ],
        self.interface.cvars['buildstamp-file'],
      ],
      'output': [
        [ join(self.interface.SOFTWARE_STORE,
               f.get('path/text()'),
               f.get('@id')) \
          for f in self.i_locals.xpath('//image') ],
      ]
    })

  def force(self):
    self.interface.log(0, "forcing initrd-image")
    self.remove_files(self.handlers['output'].oldoutput.keys())
  
  def check(self):
    if self.interface.isForced('initrd-image') or self.test_diffs():
      if not self.interface.isForced('initrd-image'):
        self.interface.log(0, "cleaning initrd-image")
        self.remove_files(self.handlers['output'].oldoutput.keys())
      return True
    else:    
      return False
  
  def run(self):
    self.interface.log(0, "processing initrd.img")
    
    # modify initrd.img - see ImageModifyMixin.modify() in lib.py
    self.modify()
    
    self.interface.cvars['isolinux-changed'] = True
  
  def apply(self):
    for file in self.DATA['output']:
      if not exists(join(self.interface.SOFTWARE_STORE, file)):
        raise RuntimeError, "Unable to find '%s' at '%s'" % (file, join(self.interface.SOFTWARE_STORE))

    initrd = self.i_locals.get('//image[@id="initrd.img"]')
    self.interface.cvars['initrd-file'] = join(self.interface.SOFTWARE_STORE,
                                               initrd.get('path/text()'), 'initrd.img')

  def generate(self):
    ImageModifyMixin.generate(self)
    self.add_file(self.interface.cvars['buildstamp-file'], '/')

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
