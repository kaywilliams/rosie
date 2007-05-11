import os

from ConfigParser import ConfigParser
from os.path      import join, exists
from StringIO     import StringIO

import dims.filereader as filereader
import dims.shlib      as shlib

from dims.osutils import *
from dims.sync    import sync

from event     import EVENT_TYPE_META, EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface, LocalsMixin
from main      import BOOLEANS_TRUE
from output    import *
from locals    import L_LOGOS

try:
  import Image
  import ImageDraw
  import ImageFilter
  import ImageFont
except ImportError:
  raise ImportError, "missing 'python-imaging' RPM"

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


#------ INTERFACES/MIXINS ------#
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

class RpmsInterface(EventInterface, RpmsMixin, OutputEventMixin, LocalsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    RpmsMixin.__init__(self)
    OutputEventMixin.__init__(self)
    LocalsMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' %(self.getBaseStore(),)),
                         base.IMPORT_DIRS)

  def append_cvar(self, flag, value):
    if flag in self._base.mvars.keys():
      if type(value) == list:
        self._base.mvars[flag].extend(value)
      else:
        self._base.mvars[flag].append(value)
    else:
      if type(value) == list:
        self._base.mvars[flag] = value
      else:
        self._base.mvars[flag] = [value]


#------ HOOK FUNCTIONS ------#
def prestores_hook(interface):
  localrepo = join(interface.getMetadata(), 'localrepo/')
  mkdir(localrepo)
  interface.add_store(STORE_XML % localrepo)

def postRPMS_hook(interface):
  interface.createrepo()
  #pkgs = find(interface.LOCAL_REPO, '*.[Rr][Pp][Mm]',
  #            nregex='.*src.[Rr][Pp][Mm]',prefix=False)
  pkgs = find(interface.LOCAL_REPO, '*.[Rr][Pp][Mm]', prefix=False)
  pkgsfile = join(interface.getMetadata(), 'dimsbuild-local.pkgs')
  if len(pkgs) > 0:
    filereader.write(pkgs, pkgsfile)  

def postrepogen_hook(interface):
  cfgfile = interface.get_cvar('repoconfig')
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
        
def release_hook(interface):
  interface.log(0, "processing release")
  handler = getHandler('release')
  interface.modify(handler)

def postrelease_hook(interface):
  handler = getHandler('release')
  if handler.create:
    # add rpms to the included-packages control var, so that
    # they are added to the comps.xml
    interface.append_cvar('included-packages', [handler.rpmname])    
    # add rpms to the excluded-packages control var, so that
    # they are removed from the comps.xml
    interface.append_cvar('excluded-packages', handler.obsoletes.split())
    
def prelogos_hook(interface):
  handler = LogosRpmHandler(interface, LOGOS_MD_STRUCT)
  addHandler(handler, 'logos')
  interface.disableEvent('logos')
  if interface.pre(handler) or (interface.eventForceStatus('logos') or False):
    interface.enableEvent('logos')
  osutils.mkdir(join(interface.getMetadata(), 'images-src/product.img'), parent=True)
        
def logos_hook(interface):
  interface.log(0, "processing logos")
  handler = getHandler('logos')
  interface.modify(handler)

def postlogos_hook(interface):
  handler = getHandler('logos')
  if handler.create:
    # add rpms to the included-packages control var, so that
    # they are added to the comps.xml
    interface.append_cvar('included-packages', [handler.rpmname])
    
    # add rpms to the excluded-packages control var, so that
    # they are removed from the comps.xml
    interface.append_cvar('excluded-packages', handler.obsoletes.split())
  

#-------- HANDLER DICTIONARY ---------#
# dictionary of semi-permanent handlers so that I can keep one instance
# around between two hook functions
HANDLERS = {}
def addHandler(handler, key): HANDLERS[key] = handler
def getHandler(key): return HANDLERS[key]


#--------------- FUNCTIONS ------------------#
def getProvides(rpmPath):
    "Returns the list of items provided by the RPM specified by rpmPath."
    ts = rpm.TransactionSet()
    fd = os.open(rpmPath, os.O_RDONLY)
    h = ts.hdrFromFdno(fd)
    del ts
    provides = h['providename']    
    os.close(fd)
    return provides    

def buildRpm(path, rpm_output, changelog=None, logger='rpmbuild',
             functionName='main', keepTemp=True, createrepo=False,
             quiet=True):
    # keepTemp should be True if path points to a location inside
    # the builddata/ folder, because if keepTemp is False, path
    # is going to get deleted once the rpm build process is complete.
    eargv = ['--bdist-base', '/usr/src/redhat',
             '--rpm-base', '/usr/src/redhat/']

    mkrpm.build(path, rpm_output, changelog=changelog, logger=logger,
                functionName=functionName, keepTemp=keepTemp, createrepo=createrepo,
                quiet=quiet, eargv=eargv)
    
    # need to delete the dist folder, because the RPMS have been copied
    # already to wherever they need to be. 
    rm(join(path, 'dist'), recursive=True, force=True)

        
#---------- HANDLERS -------------#
class RpmHandler(OutputEventHandler):
  def __init__(self, interface, data, elementname=None, rpmname=None,
               provides=None, provides_test=None, obsoletes=None,
               description=None, long_description=None):
    if len(data['output']) > 1:
      raise Exception, "only one item should be specified in data['output']"
        
    self.interface = interface    
    self.config = self.interface.config
    self.metadata = self.interface.getMetadata()
    self.software_store = self.interface.getSoftwareStore()
    self.rpm_output = join(self.metadata, 'localrepo/')

    self.fullname = self.config.get('//main/fullname/text()')
    self.version = self.config.get('//main/version/text()')

    self.elementname = elementname or 'UNKNOWN'
    self.rpmname = rpmname or 'UNKNOWN'
    self.provides = provides or 'UNKNOWN'
    self.provides_test = provides_test or 'UNKNOWN'
    self.obsoletes = self.config.get('//%s/obsoletes/text()' %(self.elementname,), None) or obsoletes or 'UNKNOWN'
    self.description = description or 'UNKNOWN'
    self.long_description = long_description or 'UNKNOWN'
    self.author = 'dimsbuild'
    self.output_location = join(self.metadata, self.elementname)

    self.log = self.interface.log
         
    self._set_method()
    
    OutputEventHandler.__init__(self, self.config, data, None,
                                mdfile=join(self.metadata, '%s.md' %(self.elementname,)),
                                mddir=self.output_location)
    
  def _set_method(self):
    if self.config.get('//%s/create/text()' %(self.elementname,), 'True') in BOOLEANS_TRUE:
      self.create = True
    else:
      self.create = False

  def removeObsoletes(self):
    for rpm in find(location=self.rpm_output, name='%s*[Rr][Pp][Mm]'):
      rm(rpm, force=True)
    rm(self.output_location, recursive=True, force=True)

  removeInvalids = removeObsoletes

  def testInputChanged(self):
    # if self.create is False, skip the RPM creation
    return self.create and OutputEventHandler.testInputChanged(self)
  
  def testInputValid(self): return True

  testOutputValid = testInputValid

  def getInput(self):
    if not exists(self.rpm_output):
      mkdir(self.rpm_output, parent=True)
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)    
    if self.create and self.data.has_key('input'):
        for input in self.data['input']:
          sync(input, self.output_location)

  def addOutput(self):
    if self.create:
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
    self.log(1, "'%s' release number: %s" %(self.elementname, new_release,))
    return new_release

  def _get_data_files(self): raise NotImplementedError # HAS to be implemented by the child class

class ReleaseRpmHandler(RpmHandler, MorphStructMixin):
  def __init__(self, interface, data):
    # expand the xpath queries in the data struct
    MorphStructMixin.__init__(self, interface.config)
    
    RpmHandler.__init__(self, interface, data,
                        elementname='release-rpm',
                        rpmname='%s-release' %(interface.product,),
                        provides_test='redhat-release',
                        provides='redhat-release',
                        obsoletes = 'fedora-release redhat-release '
                                    'centos-release redhat-release-notes '
                                    'fedora-release-notes '
                                    'centos-release-notes',
                        description='distribution release files',
                        long_description='distribution release files; '
                          'autogenerated by dimsbuild')
    
    if self.data.has_key('input'):
      self.expandInput(self.data)
    if self.data.has_key('output'):      
      self.expandOutput(self.data, dirname(self.software_store)) # the 'output' element has entries
                                                                 # relative to dirname(software_store)
    
    self.prefix = dirname(self.software_store) # prefix to the directories in data['output']
    
    if not exists(self.software_store):
      mkdir(self.software_store, parent=True)    
    
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
                        elementname='logos-rpm',
                        rpmname='%s-logos' %(interface.product,),
                        provides_test='redhat-logos',
                        provides='system-logos, redhat-logos = 4.9.3',
                        obsoletes = 'fedora-logos centos-logos redhat-logos',
                        description='Icons and pictures related to %s' \
                          %(interface.config.get('//main/fullname/text()'),),
                        long_description='The %s-logos package contains '
                          'image files which have been automatically created '
                          'by dimsbuild and are specific to the %s '
                          'distribution.' \
                          %(interface.product, interface.config.get('//main/fullname/text()'),))

    if self.data.has_key('input'):
      self.expandInput(self.data)
    if self.data.has_key('output'):      
      self.expandOutput(self.data, dirname(self.metadata)) # the 'output' element has entries
                                                           # relative to dirname(self.metadata)
    
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
      file_name = basename(id)
      dir_name = dirname(id)
      self.controlset[id] = {
        'install_path': install_path,
        'file_name': file_name,
        'dir_name': dir_name,
        }      
      for optional_item in ['width', 'height', 'textmaxwidth', 'textvcenter', 'texthcenter']:
        value = get_value(logo, optional_item, optional=True)
        if value:
          self.controlset[id][optional_item] = int(value)
        else:
          self.controlset[id][optional_item] = None

  def testOutputValid(self):
    if self.create:
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
            self.log(4, "file '%s' has invalid dimensions" %(file,))
            return False
    return True
            
  def addOutput(self):
    if self.create:
      # get the font file, either from the config file or the dimsbuild's shared folder
      ttf_file = self.config.get('//logos/font-file/text()', None)
      if not ttf_file:
        fallback_fonts = filter(lambda x: x.find('svn') == -1,
                                tree(join(self.share_path, 'fonts'), prefix=True,
                                     type='f|l'))
        ttf_file = fallback_fonts[0]
      
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
            self.log(4, "image '%s' exists in the share/" %(id,))
            sync(shared_file, dir)
          else:
            width = self.controlset[id]['width']
            height = self.controlset[id]['height']
            textmaxwidth = self.controlset[id]['textmaxwidth']
            text_xcood = self.controlset[id]['texthcenter']
            text_ycood = self.controlset[id]['textvcenter']
            self.log(4, "creating '%s'" %(id,))
            if textmaxwidth and text_xcood and text_ycood:
              self._generate_image(file_name, width, height,
                                   font_file=ttf_file,
                                   font_size=50,
                                   text_width=textmaxwidth,
                                   text='%s %s'%(self.fullname,
                                                 self.version),
                                   text_cood=(text_xcood,text_ycood),
                                   format='png')
            else:
              self._generate_image(file_name, width, height)              
        else:
          # The file is a text file that needs to be in the logos rpm.
          # These files are found in the share/ folder. If they are not
          # found, they are skipped; this needs to change eventually.
          if os.path.exists(shared_file):
            self.log(4, "file '%s' exists in share/" %(id,))
            sync(shared_file, dir)
          else: # required text file not there in shared/ folder, passing for now
            pass
      # hack to create the splash.xpm file, have to first convert
      # the grub-splash.png to an xpm and then gzip it.
      splash_xpm = join(self.output_location, 'bootloader', 'grub-splash.xpm')
      splash_xgz = '%s.gz' % splash_xpm
      splash_png = join(self.output_location, 'bootloader', 'grub-splash.png')
      if not exists(splash_xgz):
        shlib.execute('convert %s %s' %(splash_png, splash_xpm,))
        import gzip
        infile = file(splash_xpm, 'rb')
        data = infile.read()
        infile.close()
        outfile = gzip.GzipFile(splash_xgz, 'wb')
        outfile.write(data)
        outfile.close()
      RpmHandler.addOutput(self)
        
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
    rtn = ''
    for item in items.keys():
      dir = ''.join([item, ': '])
      files = ', '.join(items[item])
      rtn = ''.join([rtn, dir, files, '\n\t'])
    return rtn
        
  def _generate_image(self, file_name, width, height, font_size=0, font_file=None, 
                      text_width=100, text=None, text_cood=(10,10), format='png'):
    """ 
    Generate an image that is added to the logos RPM and the product.img.

    @param file_name  : the name of the file to be generated
    @param width      : the width of the image
    @param height     : the height of the image
    @param font_size  : the 'starting' font size of the text on the image
    @param text       : the text to be added to the image
    @param text_cood  : coordinates of the center of the text block
    @param text_width : maximum length of the text block
    @param format     : the format of the image: png, jpeg etc.
    """
    def _get_font(width, height, xcood, ycood, textmaxwidth, text, font_file, font_size):
      startX = xcood - textmaxwidth/2
      font = ImageFont.truetype(font_file, font_size)
      (text_width, text_height) = font.getsize(text)
      startY = ycood - text_height/2
      while (text_width > textmaxwidth) or \
                ((startX+text_width) > width) or \
                ((startY+text_height) > height):
        if text_height <= 10: # have to decide on a "good" minimum font size
          break               # 10 pixels good enough?
        font_size = font_size - 2
        font = ImageFont.truetype(font_file, font_size)
        (text_width, text_height) = font.getsize(text)
        startY = ycood - text_height/2
      return font

    def get_color(xquery, fallback):
      # the python-imaging library accepts big-endian colors, this
      # function, swaps the first and the third byte in the user-specified
      # color, and returns it. HACK :(.
      color = self.config.get(xquery, fallback)
      if color.startswith('0x'):
        color = color[2:]
      color = '%s%s' % ((6-len(color))*'0', color) # prepend zeros to color
      return int('0x%s%s%s' % (color[4:], color[2:4], color[:2]), 16)
      
    im = Image.new('RGB', (width, height),
                   get_color('//%s/background-color/text()' %(self.elementname,), '0x285191'))
    # add text to the image, if specified
    if text:
      font = _get_font(width, height,
                       text_cood[0],
                       text_cood[1],
                       text_width,
                       text, font_file, font_size)
      dim = font.getsize(text)
      d = ImageDraw.Draw(im)
      d.text((text_cood[0]-dim[0]/2, text_cood[1]-dim[1]/2), text, font=font,
             fill=get_color('//%s/text-color/text()' %(self.elementname,), '0xffffff'))
    # save the image to a file
    im.save(file_name, format=format)        

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
      '//logos-rpm',
    ],
    'input': [
      '/logos-rpm/path/text()',
    ],
    'output': [
      'builddata/logos/',
    ]
  }
