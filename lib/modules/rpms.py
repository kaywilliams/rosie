import os
import dims.filereader as filereader
import dims.shlib as shlib
import sys

from ConfigParser import ConfigParser
from StringIO import StringIO
from dims.imglib import CpioImage
from dims.osutils import *
from dims.sync import sync
from event import EVENT_TYPE_META, EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface, LocalsMixin
from main import BOOLEANS_TRUE
from os.path import join, exists
from output import *
from rpmUtils.miscutils import rpm2cpio
from locals import L_LOGOS

try:
  import Image
  import ImageDraw
  import ImageFilter
  import ImageFont
except ImportError:
  print "Install the python-imaging RPM and try again."
  sys.exit(1)

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'RPMS',
    'provides': ['RPMS'],
    'requires': ['.discinfo'],
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_META,
    'requires': ['stores'],        
  },
  {
    'id': 'release',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['release-package'],
    'parent': 'RPMS',
  },
  {
    'id': 'logos',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['logos-package'],
    'parent': 'RPMS',
  },  
]

STORE_XML = ''' 
<store id="dimsbuild-local">
  <path>file://%s</path>
</store>
'''

#-------------- METADATA STRUCTS ---------#
RELEASE_MD_STRUCT = {
    'config': [
        '//main/fullname/text()',
        '//main/version/text()',
        '//release-package',    
        '//stores/*/store/gpgkey/text()',
        '//main/signing/publickey/text()',
    ],
    'input': [
        '//release-package/create/yum-repo/path/text()',
        '//stores/*/store/gpgkey/text()',
        '//main/signing/publickey/text()',
    ],
    'output': [
        'os/release-files/',
    ],   
    }

LOGOS_MD_STRUCT = {
    'config': [
        '/distro/main/fullname/text()',
        '/distro/main/version/text()',
        '//logos',
    ],
    'input': '/distro/main/logos/use/path/text()',
     'output': [
        'builddata/logos/',
    ]
  }

#-------- HANDLER DICTIONARY ---------#
# dictionary of semi-permanent handlers so that I can keep one instance
# around between two hook functions
HANDLERS = {}
def addHandler(handler, key): HANDLERS[key] = handler
def getHandler(key): return HANDLERS[key]

#------ MIXINS ------#
class RpmsMixin:
  def __init__(self):
    self.LOCAL_REPO = join(self.getMetadata(), 'localrepo/')
  
  def addRpm(self, path):
    cp(path, self.LOCAL_REPO)
  
  def createrepo(self):
    pwd = os.getcwd()
    os.chdir(self.LOCAL_REPO)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(pwd)


#--------------- FUNCTIONS ------------------#
def getProvides(rpmPath):
    """
    Returns the list of items provided by the RPM specified by
    rpmPath.
    """
    ts = rpm.TransactionSet()
    fd = os.open(rpmPath, os.O_RDONLY)
    h = ts.hdrFromFdno(fd)
    del ts
    provides = h['providename']    
    os.close(fd)
    return provides    

def extract(rpmPath, output=os.getcwd()):
    """
    Extract the contents of the RPM file specified by rpmPath to
    the output location. The rpmPath parameter can use globbing.
    
    @param rpmPath : the path to the RPM file    
    @param output  : the directory that is going to contain the RPM's
    contents
    """
    dir = tempfile.mkdtemp()
    filename = join(dir, 'rpm.cpio')
    temp_output = join(dir, 'rpm.contents')
    mkdir(temp_output)
    
    #
    # Sync the RPM down to the temporary directory
    #
    sync(rpmPath, dir)
    rpmFile = join(dir, basename(rpmPath))
    
    rpm2cpio(os.open(rpmFile, os.O_RDONLY), open(filename, 'w+'))
    cpio = CpioImage(filename)
    cpio.open(point=temp_output)
    
    if not exists(output):
      mkdir(output, parent=True)
        
    cp(''.join([temp_output, '/*']), output, force=True, recursive=True)
    rm(dir, recursive=True, force=True)

def buildRpm(path, rpm_output, changelog=None, logger='rpmbuild',
             functionName='main', keepTemp=True, createrepo=False,
             quiet=True):
    # keepTemp should be True if self.path points to a location inside
    # the builddata/ folder, because if keepTemp is False, self.path
    # is going to get deleted once the rpm build process is complete.
    eargv = ['--bdist-base', '/usr/src/redhat',
             '--rpm-base', '/usr/src/redhat/']

    mkrpm.build(path, rpm_output, changelog=changelog, logger=logger,
                functionName=functionName, keepTemp=keepTemp, createrepo=createrepo,
                quiet=quiet, eargv=eargv)
    
    # need to delete the dist folder, because the RPMS have been copied
    # already to wherever they need to be. 
    rm(join(path, 'dist'), recursive=True, force=True)

#------ INTERFACES ------#
class RpmsInterface(EventInterface, RpmsMixin, OutputEventMixin, LocalsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    RpmsMixin.__init__(self)
    OutputEventMixin.__init__(self)
    LocalsMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' %(self.getBaseStore(),)),
                         base.IMPORT_DIRS)
        
#---------- HANDLERS -------------#
class RpmHandler(OutputEventHandler):
  def __init__(self, interface, data, elementname='UNKNOWN',
               rpmname='UNKNOWN', provides='UNKNOWN', provides_test='UNKNOWN',
               obsoletes='UNKNOWN', description='UNKNOWN', long_description='UNKNOWN'):
    if len(data['output']) > 1:
      raise Exception, "only one item should be specified in data['output']"
        
    self.interface = interface    
    self.config = self.interface.config
    self.metadata = self.interface.getMetadata()
    self.rpm_output = join(self.metadata, 'localrepo/')

    self.fullname = self.config.get('//main/fullname/text()')
    self.version = self.config.get('//main/version/text()')

    self.elementname = elementname
    self.rpmname = rpmname
    self.provides = provides
    self.provides_test = provides_test
    self.obsoletes = obsoletes
    self.description = description
    self.long_description = long_description
    self.author = 'dimsbuild'
    self.output_location = join(self.metadata, self.elementname)

    self.log = self.interface.log
     
    if not exists(self.rpm_output):
      mkdir(self.rpm_output, parent=True)
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)
    
    self._set_method()
    
    OutputEventHandler.__init__(self, self.config, data, None,
                                mdfile=join(self.metadata, '%s.md' %(self.elementname,)),
                                mddir=self.output_location)
    
  def _set_method(self):
    # trying to get <use> to see if it exists, and if it does            
    # self.method is 'useexisting', else if it doesn't exist
    # an XmlPathError.
    if self.config.get('//%s/use' %(self.elementname,), None):
      if self.config.get('%s/create' %(self.elementname,), None):
        raise XmlPathError, "The create and use elements in %s are mutually exclusive."\
              " Only one of them should be specified" %(self.elementname,)
      self.method = 'useexisting'
    else:
      self.method = 'create'

  def removeObsoletes(self): pass
  def removeInvalids(self): pass

  def testInputValid(self):
    if self.method == 'useexisting':
      rpmPath = self.config.get('//%s/use/path/text()' %(self.elementname,), None)
      if not rpmPath:
        self.log(2, "no RPM was specified in the config file for %s" %(self.elementname,))
        return False
      if self.provides_test not in getProvides(rpmPath):
        self.log(2, "the user-provided RPM doesn't provided %s" %(self.provides_test,))
        return False
    return True

  def testOutputValid(self): return True

  def getInput(self):
    if self.method == 'useexisting':
      rpmPath = self.config.get('//%s/use/path/text()' %(self.elementname,))
      # by this time, we know that the rpmPath is not None, because otherwise
      # testInputValid() would have returned False and we wouldn't have gotten
      # this far
      extract(rpmPath, self.output_location)
      sync(rpmPath, self.rpm_output)
    else: # self.method == 'create'
      for input in self.data['input']:
        sync(input, self.output_location)

  def addOutput(self):
    if self.method == 'create':
      self._setup()
      buildRpm(self.output_location, self.rpm_output)
      
  def _setup(self):
    setup_cfg = join(self.output_location, 'setup.cfg')
    if exists(setup_cfg):
      return
    parser = ConfigParser()
    
    parser.add_section('pkg_data')        
    parser.set('pkg_data', 'name', self.rpmname)
    parser.set('pkg_data', 'version', self.version)
    parser.set('pkg_data', 'long_description', self.long_description)
    parser.set('pkg_data', 'description', self.description)
    parser.set('pkg_data', 'author', self.author)
    parser.set('pkg_data', 'data_files', self._get_data_files())
    
    parser.add_section('bdist_rpm')
    parser.set('bdist_rpm', 'release', self._get_release())
    parser.set('bdist_rpm', 'distribution_name', self.fullname)
    parser.set('bdist_rpm', 'provides', self.provides)
    parser.set('bdist_rpm', 'obsoletes', self.obsoletes)
    
    f = open(setup_cfg, 'w')
    parser.write(f)
    f.close()
    
  def _get_release(self):
    autoconf = join(dirname(self.config.file), 'distro.conf.auto')

    new_release = None
    ad = None

    if exists(autoconf):
      ad = xmltree.read(autoconf)
      root = ad.getroot()
      old_release = root.iget('//%s/create/release/text()' %(self.elementname,))
      if old_release:
        new_release = str(int(old_release)+1)
        create_package = root.iget('//%s/create' %(self.elementname,))
        # TODO: raise exception if not found? We are creating this file, so maybe
        # it's OK to not raise an exception 
        create_package.remove(root.get('//%s/create/release' %(self.elementname,), [])[0]) 
        
    if not new_release:
      if ad:
        document_root = ad.getroot()
      else:
        document_root = xmltree.Element('auto')
        ad = xmltree.XmlTree(document_root)
      parent_node = xmltree.Element(self.elementname, parent=document_root)            
      new_release = '1'
      create_package = xmltree.Element('create', parent=parent_node)
      
    xmltree.Element('release', parent=create_package, text=new_release)            
    ad.write(autoconf)
    self.log(2, "the %s RPM's release number is %s" %(self.elementname, new_release,))
    return new_release

  def _get_data_files(self): pass # HAS to be implemented by the child class

class ReleaseRpmHandler(RpmHandler, MorphStructMixin):
  def __init__(self, interface, data):
    # expand the xpath queries in the data struct
    MorphStructMixin.__init__(self, interface.config)
    
    RpmHandler.__init__(self, interface, data,
                        elementname='release-package',
                        rpmname='%s-release' %(interface.product,),
                        provides_test='redhat-release',
                        provides='redhat-release',
                        obsoletes = 'fedora-release redhat-release centos-release '\
                        'redhat-release-notes fedora-release-notes centos-release-notes',
                        description='The Release RPM',
                        long_description='The Release RPM built by dimsbuild')

    self.software_store = interface.getSoftwareStore()
    
    self.expandInput(self.data)
    self.expandOutput(self.data, dirname(self.software_store)) # the 'output' element has entries
                                                               # relative to dirname(software_store)
    
    self.prefix = dirname(self.software_store) # prefix to the directories in data['output']
    
    if not exists(self.software_store):
      mkdir(self.software_store, parent=True)    
        
  def removeObsoletes(self):
    for location in self.data['output']:
      location = join(self.prefix, location)
      rm(location, recursive=True, force=True)
      
  def removeInvalids(self):
    self.removeObsoletes()
    
  def getInput(self):
    RpmHandler.getInput(self)
    
    find_files = []
    find_folders = []
    for file in self.config.mget('//release-package/include-in-tree/file/text()'):
      find_files.append(file)
    for folder in self.config.mget('//release-package/include-in-tree/folder/text()'):
      find_folders.append(folder)
    if self.config.get('//release-package/include-in-tree/@use-default-set', 'True') in BOOLEANS_TRUE:
      find_files.extend([
        'eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README', '*RPM-GPG',
        'RPM-GPG-KEY', 'RPM-GPG-KEY-beta', 'README-BURNING-ISOS-en_US.txt',
        'RELEASE-NOTES-en-US.html',
        ])
      find_folders.extend([
        'stylesheet-images',
        ])
      
    files = []
    folders = []
    for file in find_files:
      files.extend(find(location=self.output_location, name=file, type=TYPE_FILE))
      files.extend(find(location=self.output_location, name=file, type=TYPE_LINK))
    for folder in find_folders:
      folders.extend(find(location=self.output_location, name=folder, type=TYPE_DIR))
      
    for file in files:
      sync(file, self.software_store)
    for folder in folders:
      sync(folder, self.software_store)

  def _get_data_files(self):
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    files = tree(self.output_location, type='f|l', prefix=False)
    for file in files:
      f.write('%s\n' %(file,))
      f.close()
    config_option = '/usr/share/%s-release-notes-%s :'
    value = ', '.join(files)
    return ''.join([config_option, value])

class LogosRpmHandler(RpmHandler, MorphStructMixin):
  #
  # TODO: Add text formatting nodes' handling
  #
  def __init__(self, interface, data):      
    MorphStructMixin.__init__(self, interface.config)        

    RpmHandler.__init__(self, interface, data,
                        elementname='logos',
                        rpmname='%s-logos' %(interface.product,),
                        provides_test='redhat-logos',
                        provides='system-logos = 4.9.3, redhat-logos = 4.9.3',
                        obsoletes = 'fedora-logos centos-logos redhat-logos',
                        description="Icons and pictures related to %s" %(interface.config.get('//main/fullname/text()'),),
                        long_description="The %s-logos package contains image files "\
                        "which have been automatically created by dimsbuild and are specific "\
                        "to the %s distribution." %(interface.product, interface.config.get('//main/fullname/text()'),))

    self.expandOutput(self.data, dirname(self.metadata)) # the paths in self.data['output'] are
                                                         # relative to dirname(self.metadata)
    self.expandInput(self.data)
    
    self.share_path = self.interface._base.sharepath
    self.locals = self.interface.locals
    self.build_controlset()
    
  def build_controlset(self):
    def get_value(logo, name, optional=False):
      try:
        return logo.iget(name).text
      except AttributeError:
        if optional:
          return None
        else:
          raise
    self.controlset = {}
    logos = self.locals.getLocalPath(L_LOGOS, '/logos')
    for logo in logos.get('logo', fallback=[]):
      id = logo.attrib['id']
      install_path = get_value(logo, 'location')
      width = get_value(logo, 'width', optional=True)
      if width:
        width = int(width)            
      height = get_value(logo, 'height', optional=True)
      if height:
        height = int(height)
      file_name = basename(id)
      dir_name = dirname(id)
      self.controlset[id] = {
        'install_path': install_path,
        'width': width,
        'height': height,
        'file_name': file_name,
        'dir_name': dir_name,
        }
    
  def removeObsoletes(self):
    """
    Remove the files that are specified in self.mdfile that do not
    match the files in the input set.
    """
    if self.mdvalid:
      for file in self._get_obsoletes():
        rm(file, force=True)
        
  def removeInvalids(self):
    """
    Remove the files that are specified in self.mdfile that do not
    match the files in the output set.
    """
    if self.mdvalid:            
      for file in self._get_invalids():
        rm(file, force=True)
        
  def testOutputValid(self):
    if self.method == 'create':
      if self.data.has_key('output'):
        for id in self.controlset.keys():
          file = join(self.output_location, id)
          # TODO: Fail if a file in the control list is not found
          if file[-3:].lower() == 'xpm':
            # assume that all xpm files are fine, because the python-imaging
            # chokes on them. The xpm files used in the logos RPM are static
            # ones, so it is "fine" to make this assumption. 
            continue               
          if not self._verify_file(file, self.controlset[id]):
            self.log(2, "file %s has invalid dimensions" %(file,))
            return False
    return True
            
  def addOutput(self):
    if self.method == 'create':
      for id in self.controlset.keys():
        shared_file = join(self.share_path, 'logos', id)
        file_name = join(self.output_location, id)
        dir = dirname(file_name)
        if os.path.exists(file_name):
          continue
        if not os.path.isdir(dir):
          mkdir(dir, parent=True)
        if self.controlset[id]['width'] and self.controlset[id]['height']:
          if os.path.exists(shared_file):
            self.log(2, "image %s exists in the share/" %(id,))
            sync(shared_file, dir)
          else:
            width = self.controlset[id]['width']
            height = self.controlset[id]['height']
            self.log(2, "creating %s" %(id,))
            self._generate_image(file_name,
                                 width,
                                 height,                 
                                 50,
                                 text='%s %s'%(self.fullname,
                                               self.version))
        else:
          # The file is a text file that needs to be in the logos rpm.
          # These files are found in the share/ folder. If they are not
          # found, they are skipped; this needs to change eventually.
          if os.path.exists(shared_file):
            self.log(2, "file %s exists in share/" %(id,))
            sync(shared_file, dir)
      # hack to create the splash.xpm file
      splash_xpm = join(self.output_location, 'bootloader', 'grub-splash.xpm')
      splash_xgz = ''.join([splash_xpm, '.gz'])
      splash_png = join(self.output_location, 'bootloader', 'grub-splash.png')
      if not exists(splash_xgz):
        shlib.execute('convert %s %s' %(splash_png, splash_xpm,))
        shlib.execute('gzip %s' %(splash_xpm,))
      RpmHandler.addOutput(self)    
    # create the builddata/logos/product.img folder all the time,
    # even if the user provided the RPM. 
    self.createPixmaps()
    self.interface.setFlag('logos-changed', True)

  def createPixmaps(self):
    """
    Create the product.img folder that can be used by the
    product.img module.
    """
    # create the product.img folder/ if it doesn't exist
    product_img = join(self.output_location, 'product.img')
    if not exists(product_img):
      product_images = []
      # copy the logos from the anaconda folder and pixmaps folder
      # to builddata/logos/product.img
      mkdir(product_img)
      if self.method == 'useexisting':
        # look at the RPM/usr/share/anaconda folder for files
        dirs_to_look = [join(self.output_location, 'usr', 'share', 'anaconda')]
      else:
        # look at builddata/logos/anaconda for files to put in product.img
        dirs_to_look = [join(self.output_location, 'anaconda')]
        
      # generate the list of files to use
      for folder in dirs_to_look:
        product_images.extend(tree(folder, prefix=True, type='f|l'))

      # look at the config files for other files to put in the product.img
      if self.config.get('//logos/include-in-product-img/@use-default-set',
                         'False') in BOOLEANS_TRUE:
        files = self.config.mget('//logos/include-in-product-img/file/text()', [])
        folders = self.config.mget('//logos/include-in-product-img/folder/text()',
                                   [])
        product_images.extend(files)                
        for folder in folders:
          product_images.extend(tree(folder, prefix=True, type='f|l'))
          
      # now copy the files from the user-specified locations to this folder.
      # If the file already exists, it is removed and the user-specified one
      # is used.
      for image in product_images:
        file_name = basename(image)
        self.log(2, "hardlinking %s to %s" %(file_name, product_img,))
        os.link(image, join(product_img, file_name))                    
        
  def _get_data_files(self):
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    items = {}
    for id in self.controlset.keys():
      file = join(self.output_location, id)
      file_name = basename(file)
      file_dir = dirname(file)
      
      install_file = self.controlset[id]['install_path']
      install_filename = basename(install_file)            
      install_dir = dirname(install_file)
      
      if os.path.exists(file):
        if file_name != install_filename:
          new_file = join(file_dir, install_filename)
          os.link(file, new_file)
          id = join(file_dir, install_filename)
          if install_dir in items.keys():
            items[install_dir].append(id)
          else:
            items[install_dir] = [id]
            f.write('%s\n' %(id,))
    f.close()
    # convert items to a config-styled string
    rtn = ""
    for item in items.keys():
      dir = "".join([item, ': '])
      files = ', '.join(items[item])
      rtn = ''.join([rtn, dir, files, '\n\t'])
    return rtn
        
  def _generate_image(self, file_name, width, height, font_size,
                      text=None, fmt='png'):
    """Generate a captcha image"""
    # create a font object
    ttf_file = self.config.get('//logos/font-file/text()', None)
    if not ttf_file:
      fallback_fonts = filter(lambda x: x.find('svn') == -1,
                              tree(join(self.share_path, 'fonts'), prefix=True,
                                   type='f|l'))
      ttf_file = fallback_fonts[0]
      
    font = ImageFont.truetype(ttf_file, font_size)
    
    # create a new image slightly larger that the text
    im = Image.new('RGB', (width, height),
                   int(self.config.get('//logos/create/background-color/text()', '0xffffff'), 16))
    
    # add text to the image, if specified
    if text:
      dim = font.getsize(text)
      d = ImageDraw.Draw(im)
      d.text((15, 45), text, font=font,
             fill=int(self.config.get('//logos/create/text-color/text()', '0x000000'), 16))
            
    im = im.filter(ImageFilter.EDGE_ENHANCE_MORE)
    
    # save the image to a file
    im.save(file_name, format=fmt)        
        
  def _get_path_id(self, filename):
    for item in self.controlset.keys():
      if self.controlset[item]['file_name'] == filename:
        return item
    return None        

  def _verify_file(self, input, control):
    width = control['width']
    height = control['height']
    if width and height:
      control_size = (width, height)
      try:
        image = Image.open(input)
      except IOError:
        return False
      input_size = image.size
      if input_size != control_size:
        return False
    return True

  def _get_obsoletes(self):
    obsoletes = self._get_bad_files(self.input)
    return obsoletes

  def _get_invalids(self):
    invalids = self._get_bad_files(self.output)
    return invalids

  def _get_bad_files(self, fileinfo):
    bad_files = []
    for input_file in fileinfo.keys():
      if input_file[-3:].lower() == 'xpm':
        # HACK: assume that all xpm files are fine, because the python-imaging
        # chokes on them. The xpm files used in the logos RPM are static
        # ones, so it is "fine" to make this assumption. 
        continue
      id = self._get_path_id(basename(input_file))
      if not id or not os.path.exists(input_file) or \
             not self._verify_file(input_file, self.controlset[id]):
        bad_files.append(input_file)
    return bad_files

#------ HOOK FUNCTIONS ------#
def prestores_hook(interface):
  localrepo = join(interface.getMetadata(), 'localrepo/')
  mkdir(localrepo)
  interface.add_store(STORE_XML % localrepo)

def postRPMS_hook(interface):
  interface.createrepo()

def postrepogen_hook(interface):
  cfgfile = interface.getFlag('repoconfig')
  if not cfgfile: return  
  
  lines = filereader.read(cfgfile)
  
  lines.append('[dimsbuild-local]')
  lines.append('name = dimsbuild-local')
  lines.append('baseurl = file://%s' % join(interface.getMetadata(), 'localrepo/'))
  
  filereader.write(lines, cfgfile)

def prerelease_hook(interface):
  handler = ReleaseRpmHandler(interface, RELEASE_MD_STRUCT)
  addHandler(handler, 'release')
  interface.disableEvent('release')
  if interface.pre(handler) or (interface.eventForceStatus('release') or False):
    interface.enableEvent('release')
  interface.setFlag('release-changed', False)
        
def release_hook(interface):
  interface.log(0, "processing release")
  handler = getHandler('release')
  interface.modify(handler)

def prelogos_hook(interface):
  handler = LogosRpmHandler(interface, LOGOS_MD_STRUCT)
  addHandler(handler, 'logos')
  interface.disableEvent('logos')
  if interface.pre(handler) or (interface.eventForceStatus('logos') or False):
    interface.enableEvent('logos')
  interface.setFlag('logos-changed', False)
  osutils.mkdir(join(interface.getMetadata(), 'logos/product.img'), parent=True)
        
def logos_hook(interface):
  interface.log(0, "processing logos")
  handler = getHandler('logos')
  interface.modify(handler)
