import os

from os.path import join, exists

from dims import osutils

from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import DiffMixin

from lib import FileDownloadMixin, ImageModifyMixin

API_VERSION = 4.1

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'isolinux',
    'provides': ['vmlinuz', 'isolinux-changed'],
    'requires': ['anaconda-version', 'source-vars', 'initrd.img'], #! 'initrd.img' for run-before functionality
    'parent': 'INSTALLER',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
  {
    'id': 'initrd-image',
    'provides': ['initrd.img', 'isolinux-changed'],
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
class IsolinuxHook(FileDownloadMixin, DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.isolinux'
    
    self.interface = interface
    
    self.isolinux_dir = join(self.interface.SOFTWARE_STORE, 'isolinux') #! not versioned

    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    self.mdfile = join(self.interface.METADATA_DIR, 'isolinux.md')
    
    FileDownloadMixin.__init__(self, interface, self.interface.getBaseRepoId())
    DiffMixin.__init__(self, self.mdfile, self.DATA)
  
  def setup(self):
    self.register_file_locals(L_FILES)
    
    repo = self.interface.getRepo(self.interface.getBaseRepoId())
    
    self.DATA['input'].extend(  [ join(self.interface.INPUT_STORE,
                                       repo.id, repo.directory,
                                       f.get('path/text()'),
                                       f.get('@id')) \
                                  for f in self.f_locals.xpath('//file') ] )
    self.DATA['output'].extend( [ join(self.interface.SOFTWARE_STORE,
                                       f.get('path/text()'),
                                       f.get('@id')) \
                                   for f in self.f_locals.xpath('//file') ] )
  
  def force(self):
    for file in self.DATA['output']:
      osutils.rm(file, recursive=True, force=True)
    self.clean_metadata()
  
  def check(self):
    if self.test_diffs():
      self.force()
      return True
    else:    
      return False
  
  def run(self):
    self.interface.log(0, "synchronizing isolinux files")
    
    osutils.mkdir(self.isolinux_dir, parent=True)
    
    # download all files - see FileDownloadMixin.download() in lib.py
    self.download()
    
    self.interface.cvars['isolinux-changed'] = True
  
  def apply(self):
    for file in self.DATA['output']:
      if not exists(file):
        raise RuntimeError, "Unable to find '%s'" % file
    
    self.write_metadata()


class InitrdHook(ImageModifyMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.bootiso.initrd'
    
    self.interface = interface
    
    self.DATA = {
      'config':    ['/distro/main/product/text()',
                    '/distro/main/version/text()',
                    '/distro/main/fullname/text()',
                    '/distro/installer/initrd.img/path'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [interface.config.xpath('/distro/installer/initrd.img/path/text()', [])],
      'output':    [] # to be filled later
    }
    
    ImageModifyMixin.__init__(self, 'initrd.img', interface, self.DATA)
  
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def setup(self):
    self.register_image_locals(L_IMAGES)

    repo = self.interface.getRepo(self.interface.getBaseRepoId())
    
    self.DATA['input'].extend(  [ join(self.interface.INPUT_STORE,
                                       repo.id, repo.directory,
                                       f.get('path/text()'),
                                       f.get('@id')) \
                                  for f in self.i_locals.xpath('//image') ] )
    self.DATA['output'].extend( [ join(self.interface.SOFTWARE_STORE,
                                       f.get('path/text()'),
                                       f.get('@id')) \
                                  for f in self.i_locals.xpath('//image') ] )
    self.addInput(self.interface.cvars['buildstamp-file'])
    
  
  def force(self):
    osutils.rm(self.mdfile, force=True)
  
  def check(self):
    if self.test_diffs():
      self.force()
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
