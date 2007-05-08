import time
import os

from os.path import join, exists

import dims.filereader    as filereader
import dims.imglib        as imglib
import dims.osutils       as osutils
import dims.sync          as sync
import dims.FormattedFile as ffile

from dims.xmltree import XmlPathError, read

from interface import EventInterface, LocalsMixin
from output    import MorphStructMixin, OutputEventMixin, OutputEventHandler
from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR, EVENT_TYPE_META
from locals    import L_BUILDSTAMP, L_FILES, L_IMAGES, L_INSTALLCLASS
from main      import BOOLEANS_TRUE, BOOLEANS_FALSE
from magic     import FILE_TYPE_GZIP, FILE_TYPE_EXT2FS, FILE_TYPE_CPIO, FILE_TYPE_SQUASHFS
from callback  import BuildSyncCallback

API_VERSION = 3.0

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')
IMAGES = ['initrd.img', 'product.img', 'updates.img'] # images processed in this module

#--------- EVENT DECLARATIONS ----------#
EVENTS = [
  {
    'id': 'IMAGES',
    'provides': ['IMAGES'],
    'requires': ['.discinfo', 'comps.xml', 'software'],
    'properties': EVENT_TYPE_META,
  },
  {
    'id': 'initrd',
    'interface': 'ImageInterface',
    'provides': ['initrd.img', '.buildstamp'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'IMAGES',
  },
  {
    'id': 'product',
    'interface': 'ImageInterface',
    'provides': ['product.img'],
    'requires': ['.buildstamp'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'IMAGES',
  },
  {
    'id': 'updates',
    'interface': 'ImageInterface',
    'provides': ['updates.img'],
    'requires': ['.buildstamp'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'IMAGES',
  },
  {
    'id': 'stage2',
    'interface': 'ImageInterface',
    'provides': ['stage2'],
    'requires': ['.discinfo'],
    'parent': 'IMAGES',
  },
]

#---------- IMAGE METADATA -----------#
INITRD_MD_STRUCT = {
  'config': ['/distro/main/product/text()',
             '/distro/main/version/text()',
             '/distro/main/fullname/text()',
             '/distro/main/initrd-src/text()'],
  'variables': ['anaconda_version'],
  'input':  '/distro/main/initrd-src/text()',
}

PRODUCT_MD_STRUCT = {
  'config': ['/distro/main/product/text()',
             '/distro/main/version/text()',
             '/distro/main/fullname/text()',
             '/distro/main/product-src/text()'],
  'variables': ['anaconda_version'],
  'input':  '/distro/main/product-src/text()',
}

UPDATES_MD_STRUCT = {
  'config': ['/distro/main/product/text()',
             '/distro/main/version/text()',
             '/distro/main/fullname/text()',
             '/distro/main/updates-src/text()'],
  'variables': ['anaconda_version'],
  'input':  '/distro/main/updates-src/text()',
}

# mappings of locals file types to magic file types (semi-hack)
MAGIC_MAP = {
  'ext2': FILE_TYPE_EXT2FS,
  'cpio': FILE_TYPE_CPIO,
  'squashfs': FILE_TYPE_SQUASHFS,
}

#-------- HANDLER DICTIONARY ---------#
# dictionary of semi-permanent handlers so that I can keep one instance
# around between two hook functions
HANDLERS = {}
def addHandler(handler, key): HANDLERS[key] = handler
def getHandler(key): return HANDLERS[key]
  

#---------- INTERFACES -----------#
class ImageInterface(EventInterface, LocalsMixin, OutputEventMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    LocalsMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()),
                         self._base.IMPORT_DIRS)
    OutputEventMixin.__init__(self)
  
  def getImageFile(self, filename):
    FILE = self.getLocalPath(L_FILES, 'file[@id="%s"]' % filename)
    path = join(self.getSoftwareStore(),
                printf_local(FILE.iget('path'), self.getBaseVars()),
                filename)
    return path
  

#-------- HANDLER CLASSES ---------#
class ImageHandler:
  def __init__(self, interface, locals):
    self.name = 'super' # subclasses override this
    self.image = None
    self.interface = interface
    self.locals = locals

    self.vars = interface.getBaseVars()
    # test variables
    self.anaconda_version = interface.anaconda_version
  
  def open(self):
    FILE = self.locals.getLocalPath(L_FILES, 'file[@id="%s"]' % self.name)
    IMAGE = self.locals.getLocalPath(L_IMAGES, 'image[@id="%s"]' % self.name)
    path = self._getpath()
    format = IMAGE.iget('format/text()')
    zipped = IMAGE.iget('zipped/text()', False)
    
    if FILE.iget('virtual/text()', False):
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
    md = self.interface.getMetadata()
    osutils.mkdir(md, parent=True)
    
    buildstamp_fmt = self.locals.getLocalPath(L_BUILDSTAMP, '.')
    buildstamp = ffile.XmlToFormattedFile(buildstamp_fmt)
    try:
      base_vars = buildstamp.floread(self.image.read('.buildstamp'))
      base_vars.update(self.vars)
    except imglib.ImageIOError, e:
      base_vars = self.vars
      base_vars['timestamp'] = ANACONDA_UUID_FMT
    base_vars['webloc'] = self.interface.config.get('//main/url/text()', 'No bug url provided')
    buildstamp.write(join(md, '.buildstamp'), **base_vars)
    os.chmod(join(md, '.buildstamp'), 0644)
      
  def write_buildstamp(self):
    self.image.write(join(self.interface.getMetadata(), '.buildstamp'),
                     removeprefix=self.interface.getMetadata())
  
  def write_directory(self, dir):
    self.image.write([ join(dir, file) for file in os.listdir(dir) ],
                     removeprefix=dir)
  
  def write_filelist(self):
    filereader.write(self.image.list(),
                     join(self.interface.getMetadata(), '%s.list' % self.name))
    
  def _getpath(self):
    FILE = self.locals.getLocalPath(L_FILES, 'file[@id="%s"]' % self.name)
    path = join(self.interface.getSoftwareStore(),
                printf_local(FILE.iget('path'), self.vars),
                self.name)
    return path
 
  def _iszipped(self):
    image = self.locals.getLocalPath(L_IMAGES, 'image[@id="%s"]' % self.name)
    return image.iget('zipped/text()', 'False') in BOOLEANS_TRUE

  def validate_image(self):
    p = self._getpath()
    if not exists(p):
      return False
    else:
      if self._iszipped():
        return self.interface.verifyType(p, FILE_TYPE_GZIP)
      else:
        format = self.l_image.iget('format/text()')
        return self.interface.verifyType(p, MAGIC_MAP[format])

class InitrdImageHandler(OutputEventHandler, ImageHandler, MorphStructMixin):
  def __init__(self, interface, data):
    i,s,n,d,u,p = interface.getStoreInfo(interface.getBaseStore())
    
    initrd_path = interface.getLocalPath(L_FILES, 'file[@id="initrd.img"]/path')
    initrd_path = printf_local(initrd_path, interface.getBaseVars())
    
    self.rsrc = interface.storeInfoJoin(s, n, join(d, initrd_path, 'initrd.img'))
    self.isrc = join(interface.getInputStore(), i, d, initrd_path, 'initrd.img')
    self.username = u
    self.password = p
    self.dest = join(interface.getSoftwareStore(), initrd_path, 'initrd.img')
    self.mdfile = join(interface.getMetadata(), 'initrd.img.md')
    
    self.l_image = interface.getLocalPath(L_IMAGES, 'image[@id="initrd.img"]')

    MorphStructMixin.__init__(self, interface.config)  
    self.expandInput(data) # expand the input xpath query in struct

    OutputEventHandler.__init__(self, interface.config, data, self.isrc, self.mdfile)
    ImageHandler.__init__(self, interface, interface.locals)
    self.name = 'initrd.img'
  
  def initVars(self): pass
  # testInputChanged() defined by OutputEventHandler
  
  def testOutputValid(self):
    # TODO - expand on this, this is pretty basic
    return self.validate_image()
  
  def removeObsoletes(self):
    self.removeInvalids()
    
  def removeInvalids(self):
    osutils.rm(self.dest, force=True)
    #osutils.rm(self.mdfile, force=True)
  
  def getInput(self):
    osutils.mkdir(osutils.dirname(self.isrc), parent=True)
    sync.sync(self.rsrc, osutils.dirname(self.isrc),
                 username=self.username, password=self.password) # cachemanager this
    
  def testInputValid(self):
    return True # tested in addOutput
  
  def addOutput(self):
    self.interface.log(0, "modifying initrd.img")
    osutils.mkdir(osutils.dirname(self.dest), parent=True)
    sync.sync(self.isrc, osutils.dirname(self.dest))
    self.open() # testInputValid()
    self.generate()
    self.close()
  
  # storeMetadata() defined by OutputEventHandler
  
  def generate(self):
    initrd_dir = self.interface.config.get('//main/stores/initrd-src/text()',
                   join(osutils.dirname(self.interface.config.file), 'initrd'))
    if exists(initrd_dir):
      self.write_directory(initrd_dir)
    self.write_directory(join(self.interface.getMetadata(), 'images-src/initrd.img'))
    self.generate_buildstamp()
    self.write_buildstamp()
    self.interface.set_cvar('initrd-changed', True)

class ProductImageHandler(OutputEventHandler, ImageHandler, MorphStructMixin):
  def __init__(self, interface, data):
    product_path = interface.getLocalPath(L_FILES, 'file[@id="product.img"]/path')
    product_path = printf_local(product_path, interface.getBaseVars())
    
    self.dest = join(interface.getSoftwareStore(), product_path, 'product.img')
    self.mdfile = join(interface.getMetadata(), 'product.img.md')
    
    self.l_image = interface.getLocalPath(L_IMAGES, 'image[@id="product.img"]')

    MorphStructMixin.__init__(self, interface.config)        
    self.expandInput(data) # expand the input xpath query in struct
    
    OutputEventHandler.__init__(self, interface.config, data, None, self.mdfile)
    ImageHandler.__init__(self, interface, interface.locals)
    self.name = 'product.img'
  
  def initVars(self): pass
  # testInputChanged() defined by OutputEventHandler
  
  def testOutputValid(self):
    # TODO - expand on this, this is pretty basic
    return self.validate_image()
  
  def removeObsoletes(self):
    self.removeInvalids()
    
  def removeInvalids(self):
    osutils.rm(self.dest, force=True)
    #osutils.rm(self.mdfile, force=True)
  
  def getInput(self): pass # this image is created on the fly

  def testInputValid(self):
    return True# tested in addOutput
  
  def addOutput(self):
    self.interface.log(0, "generating product.img")
    osutils.mkdir(osutils.dirname(self.dest), parent=True)
    self.open() # testInputValid()
    self.generate()
    self.close()
  
  # storeMetadata() defined by OutputEventHandler
  
  def generate(self):
    product_dirs = self.interface.config.mget('//main/stores/product-src/text()',
                     [join(osutils.dirname(self.interface.config.file), 'product')])
    product_dirs.append(join(self.interface.getMetadata(), 'images-src/product.img'))
    
    installclass_found = False
    pixmaps_found = False
    for dir in product_dirs:
      try:
        files = os.listdir(dir)
        if 'installclasses' in files: installclass_found = True
          #self.__generate_installclass()
        if 'pixmaps' in files: pixmaps_found = True
          #self.__generate_pixmaps()
        
        self.image.write([ join(dir, file) for file in files ],
                         removeprefix=dir)
      except OSError, e:
        if e.errno == 2:
          #self.__generate_installclass()
          #self.__generate_pixmaps()
          pass
        else:
          raise e
    if not installclass_found: self.__generate_installclass()
    if not pixmaps_found: self.__generate_pixmaps()
    
    self.write_buildstamp()
    self.interface.set_cvar('product-changed', True)
  
  def __generate_installclass(self):
    # I don't like this, rereading comps.xml is annoying
    tree = read(join(self.interface.getMetadata(), 'comps.xml'))
    groups = tree.get('//group/id/text()')
    defaultgroups = tree.get('//group[default/text() = "true"]/id/text()')
    
    installclass = self.interface.getLocalPath(L_INSTALLCLASS, 'text()')
    
    # try to perform %s replacement; skip if not present
    try: installclass = installclass % (defaultgroups, groups)
    except TypeError: pass
    
    osutils.mkdir(join(self.image.mount, 'installclasses'))
    filereader.write([installclass], join(self.image.mount, 'installclasses/custom.py'))
  
  def __generate_pixmaps(self):
    # For now, just copy the logos from static locations to the product.img    
    osutils.mkdir(join(self.image.mount, 'pixmaps'))
    osutils.cp(join(self.interface.getMetadata(), 'images-src/product.img/*'),
               join(self.image.mount, 'pixmaps'))

class UpdatesImageHandler(OutputEventHandler, ImageHandler, MorphStructMixin):
  def __init__(self, interface, data):
    updates_path = interface.getLocalPath(L_FILES, 'file[@id="updates.img"]/path')
    updates_path = printf_local(updates_path, interface.getBaseVars())
    
    self.dest = join(interface.getSoftwareStore(), updates_path, 'updates.img')
    self.mdfile = join(interface.getMetadata(), 'updates.img.md')
    
    self.l_image = interface.getLocalPath(L_IMAGES, 'image[@id="updates.img"]')

    MorphStructMixin.__init__(self, interface.config)        
    self.expandInput(data) # expand the input xpath query in struct

    OutputEventHandler.__init__(self, interface.config, data, None, self.mdfile)
    ImageHandler.__init__(self, interface, interface.locals)
    self.name = 'updates.img'
  
  def initVars(self): pass
  # testInputChanged() defined by OutputEventHandler
  
  def testOutputValid(self):
    # TODO - expand on this, this is pretty basic
    return self.validate_image()
  
  def removeObsoletes(self):
    self.removeInvalids()
    
  def removeInvalids(self):
    osutils.rm(self.dest, force=True)
    #osutils.rm(self.mdfile, force=True)
  
  def getInput(self): pass # this image is created on the fly

  def testInputValid(self):
    return True # tested in addOutput
  
  def addOutput(self):
    self.interface.log(0, "generating updates.img")
    osutils.mkdir(osutils.dirname(self.dest), parent=True)
    self.open() # testInputValid()
    self.generate()
    self.close()
  
  # storeMetadata() defined by OutputEventHandler
  
  def generate(self):
    updates_dirs = self.interface.config.mget('//main/stores/updates-src/text()',
                    [join(osutils.dirname(self.interface.config.file), 'updates')])
    updates_dirs.append(join(self.interface.getMetadata(), 'images-src/updates.img'))
    
    for dir in updates_dirs:
      try:
        files = os.listdir(dir)
        
        if 'pixmaps' in files:
          self.interface.errlog(0, "Warning: excluding pixmaps directory - please include modified pixmaps in product.img")
          files.remove('pixmaps')
        
        self.image.write([ join(dir, file) for file in files ],
                         removeprefix=dir)
      except OSError, e:
        if e.errno == 2:
          pass
        else:
          raise e
    
    self.write_buildstamp()
    self.interface.set_cvar('updates-changed', True)

#---------- HOOK FUNCTIONS -----------#
def init_hook(interface):
  parser = interface.getOptParser('build')

  # the following option doesn't work yet
  parser.add_option('--with-images',
                    default=None,
                    dest='with_images',
                    metavar='IMAGEDIR',
                    help='use the images found in IMAGEDIR instead of modifying/generating them')
  
  for image in IMAGES:
    osutils.mkdir(join(interface.getMetadata(), 'images-src', image), parent=True)
  
#def applyopt_hook(interface):
#  interface.setEventControlOption('initrd',  interface.options.do_images)
#  interface.setEventControlOption('product', interface.options.do_images)
#  interface.setEventControlOption('updates', interface.options.do_images)

def preinitrd_hook(interface):
  handler = InitrdImageHandler(interface, INITRD_MD_STRUCT)
  addHandler(handler, 'initrd')
  interface.disableEvent('initrd')
  if interface.pre(handler) or (interface.eventForceStatus('initrd') or False):
    interface.enableEvent('initrd')
  interface.set_cvar('initrd-changed', False)

def preproduct_hook(interface):
  handler = ProductImageHandler(interface, PRODUCT_MD_STRUCT)
  addHandler(handler, 'product')
  interface.disableEvent('product')
  if interface.pre(handler) or (interface.eventForceStatus('product') or False):
    interface.enableEvent('product')
  interface.set_cvar('product-changed', False)

def preupdates_hook(interface):
  handler = UpdatesImageHandler(interface, UPDATES_MD_STRUCT)
  addHandler(handler, 'updates')
  interface.disableEvent('updates')
  if interface.pre(handler) or (interface.eventForceStatus('updates') or False):
    interface.enableEvent('updates')
  interface.set_cvar('updates-changed', False)

def initrd_hook(interface):
  handler = getHandler('initrd')
  interface.modify(handler)

def product_hook(interface):
  handler = getHandler('product')
  interface.modify(handler)

def updates_hook(interface):
  handler = getHandler('updates')
  interface.modify(handler)

def stage2_hook(interface):
  interface.log(0, "synchronizing files")
  cb = BuildSyncCallback(interface.logthresh)
  i,_,_,d,_,_ = interface.getStoreInfo(interface.getBaseStore())
  d = d.lstrip('/') # un-absolute path d
  local_files = interface.getLocal(L_FILES)
  for file in local_files.get('file'):
    filename = file.attrib['id']
    if filename in IMAGES: continue # skip images we already process
    if file.attrib.get('virtual', 'False') in BOOLEANS_TRUE: continue # skip virtual images
    
    rinfix = printf_local(file.iget('path'), interface.getSourceVars())
    linfix = printf_local(file.iget('path'), interface.getBaseVars())
    interface.cache(join(d, rinfix, filename), prefix=i, callback=cb)
    osutils.mkdir(join(interface.getSoftwareStore(), linfix), parent=True)
    sync.sync(join(interface.getInputStore(), i, d, rinfix, filename),
              join(interface.getSoftwareStore(), linfix))


#--------- HELPER FUNCTIONS ---------#
def printf_local(elem, vars):
  string = elem.iget('string-format/string/text()', elem.text)
  format = elem.get('string-format/format/item/text()', [])
  return printf(string, format, vars)

def printf(string, fmt, vars):
  for f in fmt:
    try:
      string = string.replace('%s', vars[f], 1)
    except KeyError:
      raise KeyError, "Variable '%s' not defined in supplied scope" % f
  return string
