import os
import time

from os.path  import join, exists
from StringIO import StringIO

import dims.FormattedFile as ffile
import dims.imerge        as imerge
import dims.imglib        as imglib
import dims.osutils       as osutils
import dims.sync          as sync
import dims.xmltree       as xmltree

from callback  import BuildSyncCallback
from interface import EventInterface, VersionMixin
from locals    import printf_local
from main      import BOOLEANS_TRUE
from magic     import FILE_TYPE_GZIP, FILE_TYPE_EXT2FS, FILE_TYPE_CPIO, FILE_TYPE_SQUASHFS
from output    import OutputEventMixin, MorphStructMixin, OutputEventHandler

ANACONDA_UUID_FMT = time.strftime('%Y%m%d%H%M')

MAGIC_MAP = {
  'ext2': FILE_TYPE_EXT2FS,
  'cpio': FILE_TYPE_CPIO,
  'squashfs': FILE_TYPE_SQUASHFS
}


class InstallerInterface(EventInterface, OutputEventMixin, VersionMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    VersionMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()))
    OutputEventMixin.__init__(self)
  

class ImageHandler:
  def __init__(self, interface, locals):
    self.name = 'super' # subclasses override this
    self.image = None
    self.interface = interface
    self.locals = locals
    
    self.vars = self.interface.getBaseVars()
    self.anaconda_version = self.interface.anaconda_version
  
  def open(self):
    image  = self.locals.iget('//images/image[@id="%s"]' % self.name)
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
    md = self.interface.getMetadata()
    osutils.mkdir(md, parent=True)
    
    locals = locals_imerge(L_BUILDSTAMP_FORMAT, self.interface.anaconda_version)
    
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
    self.image.write(join(self.interface.getMetadata(), '.buildstamp'), '/')
  
  def write_directory(self, dir):
    self.image.write([ join(dir, file) for file in os.listdir(dir) ], '/')
  
  def _getpath(self):
    FILE = self.locals.iget('//images/image[@id="%s"]' % self.name)
    return join(self.interface.getSoftwareStore(),
                printf_local(FILE.iget('path'), self.vars),
                self.name)
  
  def _iszipped(self):
    IMAGE = self.locals.iget('//images/image[@id="%s"]' % self.name)
    return IMAGE.iget('zipped/text()', 'False') in BOOLEANS_TRUE
  
  def _isvirtual(self):
    IMAGE = self.locals.iget('//images/image[@id="%s"]' % self.name)
    return IMAGE.iget('@virtual', 'True') in BOOLEANS_TRUE
  
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


class ImageModifier(OutputEventHandler, ImageHandler, MorphStructMixin):
  def __init__(self, name, interface, data, locals, mdfile=None):
    locals = locals_imerge(locals, interface.anaconda_version)

    i,s,n,d,u,p = interface.getStoreInfo(interface.getBaseStore())
    
    image_path = locals.iget('//images/image[@id="%s"]/path' % name)
    image_path = printf_local(image_path, interface.getBaseVars())
    
    self.rsrc = interface.storeInfoJoin(s, n, join(d, image_path, name))
    self.isrc = join(interface.getInputStore(), i, d, image_path, name)
    self.username = u
    self.password = p
    self.dest = join(interface.getSoftwareStore(), image_path, name)
    if mdfile is None:
      self.mdfile = join(interface.getMetadata(), '%s.md' % name)
    else:
      self.mdfile = mdfile
    
    self.l_image = locals.iget('//images/image[@id="%s"]' % name)
    
    MorphStructMixin.__init__(self, interface.config)
    self.expandInput(data)
    
    OutputEventHandler.__init__(self, interface.config, data, self.isrc, self.mdfile)
    ImageHandler.__init__(self, interface, locals)
    self.name = name
  
  def initVars(self): pass
  
  def testOutputValid(self): # TODO - expand on this, pretty basic
    return self.validate_image()
  
  def removeObsoletes(self):
    self.removeInvalids()
  
  def removeInvalids(self):
    osutils.rm(self.dest, force=True)
    #osutils.rm(self.mdfile, force=True)
  
  def getInput(self):
    osutils.mkdir(osutils.dirname(self.isrc), parent=True)
    # try to get the image from the input store - if its not there and image is
    # virtual, that's ok; otherwise, raise
    try:
      sync.sync(self.rsrc, osutils.dirname(self.isrc),
                username=self.username, password=self.password) # cachemanager this
    except sync.util.SyncError, e:
      if self._isvirtual(): pass
      else: raise e
  
  def testInputValid(self):
    return True # tested in addOutput
  
  def addOutput(self):
    self.interface.log(1, "modifying %s" % self.name)
    osutils.mkdir(osutils.dirname(self.dest), parent=True)
    try:
      sync.sync(self.isrc, osutils.dirname(self.dest))
    except sync.util.SyncError, e:
      if self._isvirtual(): pass
      else: raise e
    self.open() # testInputValid()
    self.generate()
    self.close()
  
  def generate(self):
    for file in self.interface.config.mget('//installer/%s/path' % self.name, []):
      src = file.iget('text()')
      dest = file.iget('@dest', '/')
      if exists(src):
        self.image.write(src, dest)
    if exists(join(self.interface.getMetadata(), 'images-src/%s' % self.name)):
      self.write_directory(join(self.interface.getMetadata(),
                                'images-src/%s' % self.name))
    self.generate_buildstamp()
    self.write_buildstamp()
    self.interface.set_cvar('%s-changed' % self.name, True)


class FileDownloader:
  def __init__(self, locals, interface):
    self.locals = locals_imerge(locals, interface.anaconda_version)
    
    self.interface = interface
    
    self.callback = BuildSyncCallback(interface.logthresh)
  
  def download(self, dest, store):
    dest = dest.lstrip('/') # make sure it is not an absolute path
    for file in self.locals.get('//files/file'):
      filename = file.attrib['id']
      if file.attrib.get('virtual', 'False') in BOOLEANS_TRUE: continue # skip virtual files
      
      rinfix = printf_local(file.iget('path'), self.interface.getSourceVars())
      linfix = printf_local(file.iget('path'), self.interface.getBaseVars())
      
      self.interface.cache(join(dest, rinfix, filename),
                           prefix=store, callback=self.callback)
      osutils.mkdir(join(self.interface.getSoftwareStore(), linfix), parent=True)
      sync.sync(join(self.interface.getInputStore(), store, dest, rinfix, filename),
                join(self.interface.getSoftwareStore(), linfix))


def locals_imerge(string, ver):
  tree = xmltree.read(StringIO(string))
  locals = xmltree.Element('locals')
  for child in tree.getroot().getchildren():
    locals.append(imerge.incremental_merge(child, ver))
  return locals


L_BUILDSTAMP_FORMAT = ''' 
<locals>
  <buildstamp-format-entries>
    <buildstamp-format version="0">
      <line id="timestamp" position="0">
        <string-format string="%s">
          <format>
            <item>timestamp</item>
          </format>
        </string-format>
      </line>
      <line id="fullname" position="1">
        <string-format string="%s">
          <format>
            <item>fullname</item>
          </format>
        </string-format>
      </line>
      <line id="version" position="2">
        <string-format string="%s">
          <format>
            <item>version</item>
          </format>
        </string-format>
      </line>
      <line id="product" position="3">
        <string-format string="%s">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
    </buildstamp-format>
    
    <!-- 10.2.0.63-1 - added '.arch' to timestamp -->
    <buildstamp-format version="10.2.0.63-1">
      <action type="update" path="line[@id='timestamp']">
        <string-format string="%s.%s">
          <format>
            <item>timestamp</item>
            <item>basearch</item>
          </format>
        </string-format>
      </action>
    </buildstamp-format>
  
    <!-- 10.1.0.1 to 10.2.1.5 (uncertain) - webloc line added -->
    <buildstamp-format version="10.2.1.5">
      <action type="insert" path=".">
        <line id="webloc" position="4">
          <string-format string="%s">
            <format>
              <item>webloc</item>
            </format>
          </string-format>
        </line>
      </action>
    </buildstamp-format>
  
  </buildstamp-format-entries>
</locals>
'''
