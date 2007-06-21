import os
import tempfile
import time

from StringIO import StringIO
from os.path  import join, exists
from rpmUtils.miscutils import rpm2cpio

from dims import FormattedFile as ffile
from dims import imerge
from dims import imglib
from dims import osutils
from dims import sync
from dims import xmltree

from callback  import BuildSyncCallback
from difftest  import InputHandler, OutputHandler
from interface import DiffMixin
from locals    import printf_local, L_BUILDSTAMP_FORMAT, L_IMAGES
from main      import BOOLEANS_TRUE, locals_imerge
from magic     import match as magic_match
from magic     import FILE_TYPE_GZIP, FILE_TYPE_EXT2FS, FILE_TYPE_CPIO, FILE_TYPE_SQUASHFS, FILE_TYPE_FAT

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')

MAGIC_MAP = {
  'ext2': FILE_TYPE_EXT2FS,
  'cpio': FILE_TYPE_CPIO,
  'squashfs': FILE_TYPE_SQUASHFS,
  'fat32': FILE_TYPE_FAT,
}


#------ HELPER FUNCTIONS ------#
def extractRpm(rpmPath, output=os.getcwd()):
  """ 
  Extract the contents of the RPM file specified by rpmPath to
  the output location. The rpmPath parameter can use globbing.
  
  @param rpmPath : the path to the RPM file    
  @param output  : the directory that is going to contain the RPM's
  contents
  """
  dir = tempfile.mkdtemp()
  try:
    filename = join(dir, 'rpm.cpio')
    
    # sync the RPM down to the temporary directory
    sync.sync(rpmPath, dir)
    rpmFile = join(dir, osutils.basename(rpmPath))
    
    rpm2cpio(os.open(rpmFile, os.O_RDONLY), open(filename, 'w+'))
    cpio = imglib.CpioImage(filename)    
    if not exists(output):
      osutils.mkdir(output, parent=True)    
    cpio.open(point=output)
  finally:
    osutils.rm(dir, recursive=True, force=True)


class ExtractHandler(DiffMixin):
  def __init__(self, interface, data, mdfile):    
    self.interface = interface
    self.config = self.interface.config
    self.software_store = self.interface.SOFTWARE_STORE
    
    DiffMixin.__init__(self, mdfile, data)

  def force(self):
    self.modify_output_data(self.handlers['output'].output.keys())
    self.clean_output()
  
  def check(self):
    self.modify_input_data(self.find_rpms())
    self.modify_output_data(self.handlers['output'].output.keys())
    if self.test_diffs():
      self.clean_output()
      return True
    return False

  def extract(self, message):
    self.interface.log(0, message)
    
    # get input - extract RPMs
    self.working_dir = tempfile.mkdtemp() # temporary directory, gets deleted once done
    for rpmname in self.data['input']:
      extractRpm(rpmname, self.working_dir)    

    # generate output files
    try:
      # need to modify self.data, so that the metadata
      # written has all the files created. Otherwise, self.data['output']
      # will be empty.
      self.modify_output_data(self.generate())
    finally:
      osutils.rm(self.working_dir, recursive=True, force=True)

    # write metadata
    self.write_metadata()

  def modify_input_data(self, input):
    self._modify('input', input)

  def modify_output_data(self, output):
    self._modify('output', output)

  def _modify(self, key, value):
    if self.data.has_key(key):
      for x in self.data[key]:
        self.data[key].remove(x)
    else:
      self.data[key] = []
      
    self.data[key].extend(value)
    
    if key not in self.handlers.keys():
      h = {
        'input':  InputHandler,
        'output': OutputHandler,
        }[key](self.data[key])
      self.DT.addHandler(h)
      self.handlers[key] = h
      
  def clean_output(self):
    if self.data.has_key('output'):
      for file in self.data['output']:
        osutils.rm(file, recursive=True, force=True)
        

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
    self.i_locals = locals_imerge(locals, self.interface.cvars['anaconda-version'])
    self.anaconda_version = self.interface.cvars['anaconda-version']
  
  def open(self):
    image  = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    path   = self._getpath()
    format = image.get('format/text()')
    zipped = image.get('zipped/text()', 'False') in BOOLEANS_TRUE
    
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
    
    buildstamp_fmt = locals.get('//buildstamp-format')
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
    FILE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return join(self.interface.SOFTWARE_STORE,
                printf_local(FILE.get('path'), self.vars),
                self.name)
  
  def _iszipped(self):
    IMAGE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return IMAGE.get('zipped/text()', 'False') in BOOLEANS_TRUE
  
  def _isvirtual(self):
    IMAGE = self.i_locals.get('//images/image[@id="%s"]' % self.name)
    return IMAGE.get('@virtual', 'True') in BOOLEANS_TRUE
  
  def validate_image(self):
    p = self._getpath()
    if not exists(p):
      return False
    else:
      if self._iszipped():
        return magic_match(p) == FILE_TYPE_GZIP
      else:
        format = self.l_image.get('format/text()')
        return magic_match(p) == MAGIC_MAP[format]


class ImageModifyMixin(ImageHandler, DiffMixin):
  "Classes that extend this must require 'anaconda-version'"
  def __init__(self, name, interface, data, mdfile=None):
    if mdfile is None:
      self.mdfile = join(interface.METADATA_DIR, '%s.md' % name)
    else:
      self.mdfile = mdfile
    
    ImageHandler.__init__(self, interface)
    DiffMixin.__init__(self, self.mdfile, data)
    
    self.name = name
  
  def register_image_locals(self, locals):
    ImageHandler.register_image_locals(self, locals)
    
    i,s,n,d,u,p = self.interface.getStoreInfo(self.interface.getBaseStore())
    
    image_path = self.i_locals.get('//images/image[@id="%s"]/path' % self.name)
    image_path = printf_local(image_path, self.interface.BASE_VARS)
    
    self.rsrc = self.interface.storeInfoJoin(s, n, join(d, image_path, self.name))
    self.isrc = join(self.interface.INPUT_STORE, i, d, image_path, self.name)
    self.username = u
    self.password = p
    self.dest = join(self.interface.SOFTWARE_STORE, image_path, self.name)
    
    self.l_image = self.i_locals.get('//images/image[@id="%s"]' % self.name)
  
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
    for file in self.interface.config.xpath('//installer/%s/path' % self.name, []):
      src = file.get('text()')
      dest = file.get('@dest', '/')
      if exists(src):
        self.image.write(src, dest)
    if exists(join(self.interface.METADATA_DIR, 'images-src/%s' % self.name)):
      self.write_directory(join(self.interface.METADATA_DIR,
                                'images-src/%s' % self.name))
    self.generate_buildstamp()
    self.write_buildstamp()
    self.interface.cvars['%s-changed' % self.name] = True


class FileDownloadMixin:
  "Classes that extend this must require 'anaconda-version' and 'source-vars'"
  def __init__(self, interface):
    self.f_locals = None
    
    self.interface = interface
    
    self.callback = BuildSyncCallback(interface.logthresh)
  
  def register_file_locals(self, locals):
    self.f_locals = locals_imerge(locals, self.interface.cvars['anaconda-version'])
  
  def download(self, dest, store):
    if not self.f_locals:
      raise RuntimeError, "FileDownloadMixin instance has no registered locals"
    dest = dest.lstrip('/') # make sure it is not an absolute path
    for file in self.f_locals.xpath('//files/file'):
      filename = file.attrib['id']
      if file.attrib.get('virtual', 'False') in BOOLEANS_TRUE: continue # skip virtual files
      
      rinfix = printf_local(file.get('path'), self.interface.cvars['source-vars'])
      linfix = printf_local(file.get('path'), self.interface.BASE_VARS)
      
      self.interface.cache(join(dest, rinfix, filename),
                           prefix=store, callback=self.callback)
      osutils.mkdir(join(self.interface.SOFTWARE_STORE, linfix), parent=True)
      sync.sync(join(self.interface.INPUT_STORE, store, dest, rinfix, filename),
                join(self.interface.SOFTWARE_STORE, linfix))

class RpmNotFoundError(Exception): pass
