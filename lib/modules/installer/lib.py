import os
import time

from os.path  import join, exists
from StringIO import StringIO

from dims import FormattedFile as ffile
from dims import imerge
from dims import imglib
from dims import osutils
from dims import sync
from dims import xmltree

from callback  import BuildSyncCallback
from locals    import printf_local, L_BUILDSTAMP_FORMAT, L_IMAGES
from main      import BOOLEANS_TRUE
from magic     import match as magic_match
from magic     import FILE_TYPE_GZIP, FILE_TYPE_EXT2FS, FILE_TYPE_CPIO, FILE_TYPE_SQUASHFS, FILE_TYPE_FAT
from output    import OutputEventHandler, OutputInvalidError

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')

MAGIC_MAP = {
  'ext2': FILE_TYPE_EXT2FS,
  'cpio': FILE_TYPE_CPIO,
  'squashfs': FILE_TYPE_SQUASHFS,
  'fat32': FILE_TYPE_FAT,
}


class ImageHandler:
  "Classes that extend this must require 'anaconda-version'"
  def __init__(self, interface):
    self.name = 'super' # subclasses override this
    self.image = None
    self.interface = interface
    self.i_locals = None
    
    self.vars = self.interface.BASE_VARS
    self.anaconda_version = None
  
  def register_image_locals(self, locals):
    self.i_locals = locals_imerge(locals, self.interface.get_cvar('anaconda-version'))
    self.anaconda_version = self.interface.get_cvar('anaconda-version')
  
  def open(self):
    image  = self.i_locals.iget('//images/image[@id="%s"]' % self.name)
    path   = self._getpath()
    format = image.iget('format/text()')
    zipped = image.iget('zipped/text()', 'False') in BOOLEANS_TRUE
    
    if image.attrib.get('virtual', 'False') in BOOLEANS_TRUE:
      if exists(path): osutils.rm(path) # delete old image
      self.image = imglib.createImage(path, format, zipped)
    else:
      self.image = imglib.Image(path, format, zipped)
    self.image.open()
  
  def close(self):
    self.image.close()
    self.image.cleanup()
  
  def generate(self):
    raise NotImplementedError
  
  def generate_buildstamp(self):
    "Generate a .buildstamp file"
    md = self.interface.METADATA_DIR
    osutils.mkdir(md, parent=True)
    
    locals = locals_imerge(L_BUILDSTAMP_FORMAT, self.anaconda_version)
    
    buildstamp_fmt = locals.iget('//buildstamp-format')
    buildstamp = ffile.XmlToFormattedFile(buildstamp_fmt)
    try:
      base_vars = buildstamp.floread(self.image.read('.buildstamp'))
      base_vars.update(self.vars)
    except imglib.ImageIOError:
      base_vars = self.vars
      base_vars['timestamp'] = ANACONDA_UUID_FMT
    base_vars['webloc'] = self.interface.config.get('//main/url/text()', 'No bug url provided')
    buildstamp.write(join(md, '.buildstamp'), **base_vars)
    os.chmod(join(md, '.buildstamp'), 0644)
  
  def write_buildstamp(self):
    self.image.write(join(self.interface.METADATA_DIR, '.buildstamp'), '/')
  
  def write_directory(self, dir):
    self.image.write([ join(dir, file) for file in os.listdir(dir) ], '/')
  
  def _getpath(self):
    FILE = self.i_locals.iget('//images/image[@id="%s"]' % self.name)
    return join(self.interface.SOFTWARE_STORE,
                printf_local(FILE.iget('path'), self.vars),
                self.name)
  
  def _iszipped(self):
    IMAGE = self.i_locals.iget('//images/image[@id="%s"]' % self.name)
    return IMAGE.iget('zipped/text()', 'False') in BOOLEANS_TRUE
  
  def _isvirtual(self):
    IMAGE = self.i_locals.iget('//images/image[@id="%s"]' % self.name)
    return IMAGE.iget('@virtual', 'True') in BOOLEANS_TRUE
  
  def validate_image(self):
    p = self._getpath()
    if not exists(p):
      return False
    else:
      if self._iszipped():
        return magic_match(p) == FILE_TYPE_GZIP
      else:
        format = self.l_image.iget('format/text()')
        return magic_match(p) == MAGIC_MAP[format]


class ImageModifier(OutputEventHandler, ImageHandler):
  "Classes that extend this must require 'anaconda-version'"
  def __init__(self, name, interface, data, mdfile=None):
    if mdfile is None:
      self.mdfile = join(interface.METADATA_DIR, '%s.md' % name)
    else:
      self.mdfile = mdfile
    
    OutputEventHandler.__init__(self, interface.config, data, self.mdfile)
    ImageHandler.__init__(self, interface)
    
    self.name = name
  
  def register_image_locals(self, locals):
    ImageHandler.register_image_locals(self, locals)
    
    i,s,n,d,u,p = self.interface.getStoreInfo(self.interface.getBaseStore())
    
    image_path = self.i_locals.iget('//images/image[@id="%s"]/path' % self.name)
    image_path = printf_local(image_path, self.interface.BASE_VARS)
    
    self.rsrc = self.interface.storeInfoJoin(s, n, join(d, image_path, self.name))
    self.isrc = join(self.interface.INPUT_STORE, i, d, image_path, self.name)
    self.username = u
    self.password = p
    self.dest = join(self.interface.SOFTWARE_STORE, image_path, self.name)
    
    self.l_image = self.i_locals.iget('//images/image[@id="%s"]' % self.name)
  
  def check_run_status(self): #!
    if self.test_input_changed():
      osutils.rm(self.dest, force=True)
      return True
    if not self.validate_image():
      ostuils.rm(self.dest, force=True)
      return True
    return False
  
  def modify(self):
    # sync image to input store
    osutils.mkdir(osutils.dirname(self.isrc), parent=True)
    # try to get image from input store - if it is not there and image is virtual,
    # that's ok; otherwise, raise
    try:
      sync.sync(self.rsrc, osutils.dirname(self.isrc),
                username=self.username, password=self.password) # cachemanager this
    except sync.util.SyncError, e:
      if self._isvirtual(): pass
      else: raise e
    
    # sync image to output store
    osutils.mkdir(osutils.dirname(self.dest), parent=True)
    try:
      sync.sync(self.isrc, osutils.dirname(self.dest))
    except sync.util.SyncError, e:
      if self._isvirtual(): pass
      else: raise e
    
    # modify image
    self.interface.log(1, "modifying %s" % self.name)
    self.open()
    self.generate()
    self.close()
    
    # validate output
    if not self.validate_image():
      raise OutputInvalidError, "output files are invalid"
    
    # write metadata
    self.write_metadata()
  
  def generate(self):
    for file in self.interface.config.mget('//installer/%s/path' % self.name, []):
      src = file.iget('text()')
      dest = file.iget('@dest', '/')
      if exists(src):
        self.image.write(src, dest)
    if exists(join(self.interface.METADATA_DIR, 'images-src/%s' % self.name)):
      self.write_directory(join(self.interface.METADATA_DIR,
                                'images-src/%s' % self.name))
    self.generate_buildstamp()
    self.write_buildstamp()
    self.interface.set_cvar('%s-changed' % self.name, True)


class FileDownloader:
  "Classes that extend this must require 'anaconda-version' and 'source-vars'"
  def __init__(self, interface):
    self.f_locals = None
    
    self.interface = interface
    
    self.callback = BuildSyncCallback(interface.logthresh)
  
  def register_file_locals(self, locals):
    self.f_locals = locals_imerge(locals, self.interface.get_cvar('anaconda-version'))
  
  def download(self, dest, store):
    if not self.f_locals:
      raise RuntimeError, "FileDownloader instance has no registered locals"
    dest = dest.lstrip('/') # make sure it is not an absolute path
    for file in self.f_locals.get('//files/file'):
      filename = file.attrib['id']
      if file.attrib.get('virtual', 'False') in BOOLEANS_TRUE: continue # skip virtual files
      
      rinfix = printf_local(file.iget('path'), self.interface.get_cvar('source-vars'))
      linfix = printf_local(file.iget('path'), self.interface.BASE_VARS)
      
      self.interface.cache(join(dest, rinfix, filename),
                           prefix=store, callback=self.callback)
      osutils.mkdir(join(self.interface.SOFTWARE_STORE, linfix), parent=True)
      sync.sync(join(self.interface.INPUT_STORE, store, dest, rinfix, filename),
                join(self.interface.SOFTWARE_STORE, linfix))


def locals_imerge(string, ver):
  tree = xmltree.read(StringIO(string))
  locals = xmltree.Element('locals')
  for child in tree.getroot().getchildren():
    locals.append(imerge.incremental_merge(child, ver))
  return locals


