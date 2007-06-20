from os.path            import join, exists, isdir, isfile
from rpmUtils.miscutils import rpm2cpio

import os
import tempfile

from dims import shlib

from dims.imglib  import CpioImage
from dims.osutils import *
from dims.sync    import sync

from difftest  import InputHandler, OutputHandler
from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import DiffMixin, EventInterface
from main      import BOOLEANS_TRUE, locals_imerge
from magic     import FILE_TYPE_JPG, FILE_TYPE_LSS, match as magic_match

try:
  import Image
except ImportError:
  raise ImportError("missing 'python-imaging' RPM")

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'installer-logos',
    'interface': 'EventInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['splash'],
    'requires': ['software'],
    'conditional-requires': ['gpgsign'],    
    'parent': 'INSTALLER',
  },
  {
    'id': 'installer-release-files',
    'interface': 'EventInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'requires': ['software'],
    'conditional-requires': ['gpgsign'],
    'parent': 'INSTALLER',
  },  
]

HOOK_MAPPING = {
  'InstallerLogosHook':   'installer-logos',
  'InstallerReleaseHook': 'installer-release-files',
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
    sync(rpmPath, dir)
    rpmFile = join(dir, basename(rpmPath))
    
    rpm2cpio(os.open(rpmFile, os.O_RDONLY), open(filename, 'w+'))
    cpio = CpioImage(filename)    
    if not exists(output):
      mkdir(output, parent=True)    
    cpio.open(point=output)
  finally:
    rm(dir, recursive=True, force=True)


class ExtractEventHandler(DiffMixin):
  def __init__(self, interface, data, mdfile):    
    self.interface = interface
    self.config = self.interface.config
    self.software_store = self.interface.SOFTWARE_STORE
    
    DiffMixin.__init__(self, mdfile, data)

  def force(self):
    self.clean_output()
  
  def check(self):
    self.modify_input_data(self.find_rpms())    
    if self.test_diffs() or self.output_changed():
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
      rm(self.working_dir, recursive=True, force=True)

    # write metadata
    self.write_metadata()

  def modify_input_data(self, input):
    self._modify('input', input)

  def modify_output_data(self, output):
    self._modify('output', output)

  def _modify(self, key, value):
    if self.data.has_key(key):
      for x in self.data[key]:
        self.data.remove(x)
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
      
  def output_changed(self):
    # have to use this output_changed() instead of DiffMixin's
    # because self.data['output'] hasn't been set yet. 
    if hasattr(self, 'output'):      
      for file in self.output.keys():
        if not exists(file):
          return True
        stats = os.stat(file)      
        if stats.st_size != int(self.output[file]['size']) or \
               stats.st_mtime != int(self.output[file]['mtime']):
          return True
    return False
  
  def clean_output(self):
    if hasattr(self, 'output'):
      for file in self.output.keys():
        rm(file, recursive=True, force=True)


#------ HOOKS ------#
class InstallerLogosHook(ExtractEventHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.rpmextract.installer-logos'

    self.metadata_struct = {
      'config'   : ['//installer/logos'],
      'variables': ['cvars[\'anaconda-version\']'],
    }
    
    ExtractEventHandler.__init__(self, interface, self.metadata_struct,
                                 join(interface.METADATA_DIR, 'installer-logos.md'))
    self.format = None
    self.splash = None

  def check(self):
    self.locals = locals_imerge(L_INSTALLER_LOGOS, self.interface.cvars['anaconda-version'])
    self.format = self.locals.get('//splash-image/format/text()')
    self.splash = join(self.software_store, 'isolinux', 'splash.%s' %self.format)
    return ExtractEventHandler.check(self)
  
  def run(self):
    ExtractEventHandler.extract(self, "processing installer logos")

  def generate(self):
    "Create the splash image and copy it to the isolinux/ folder"
    output_dir = join(self.software_store, 'isolinux')
    if not exists(output_dir):
      mkdir(output_dir, parent=True)

    # copy images to the product.img/ folder
    output = self.copy_pixmaps()

    # create the splash image
    self.generate_splash()
    output.append(self.splash)
    
    return output
  
  def generate_splash(self):
    # convert the syslinux-splash.png to splash.lss and copy it
    # to the isolinux/ folder
    splash_pngs = find(self.working_dir, 'syslinux-splash.png')
    if len(splash_pngs) == 0:
      raise SplashImageNotFound("no syslinux-splash.png found in logos RPM")
    
    splash_png = splash_pngs[0]
    if self.format == 'jpg':
      Image.open(splash_png).save(self.splash)
    else:
      shlib.execute('pngtopnm %s | ppmtolss16 \#cdcfd5=7 \#ffffff=1 \#000000=0 \#c90000=15 > %s'
                    %(splash_png, self.splash,))

  def copy_pixmaps(self):
    """ 
    Create the product.img folder that can be used by the product.img
    module.
    """
    # delete the pixmaps folder in the images-src/product.img/ folder
    # and link the images from the RPM folder to the pixmaps folder.
    product_img = join(self.interface.METADATA_DIR, 'images-src', 'product.img', 'pixmaps')
    mkdir(product_img, parent=True)

    # FIXME: is the anaconda/pixmaps folder sufficient?
    dirs_to_look = find(self.working_dir, name='pixmaps', type=TYPE_DIR, regex='.*anaconda.*')

    # generate the list of files to use and copy them to the product.img folder
    pixmaps = []    
    for folder in dirs_to_look:
      for image in find(folder, type=0101, prefix=True):
        file_name = basename(image)
        self.interface.log(4, "hardlinking %s to %s" %(file_name, product_img,))
        pixmap = join(product_img, file_name)
        sync(image, product_img, link=True)
        pixmaps.append(pixmap)
    return pixmaps

  def apply(self):
    if not self.valid_splash():
      raise RuntimeError("%s is not a valid %s file" %(self.splash, self.format))
    self.interface.cvars['splash'] = self.splash

  def valid_splash(self):
    if self.format == 'jpg':
      return magic_match(self.splash) == FILE_TYPE_JPG
    else:
      return magic_match(self.splash) == FILE_TYPE_LSS
      
  def find_rpms(self):
    pkgname = self.config.get('//installer/logos/package/text()',
                              '%s-logos' %(self.interface.product,))
    rpms = find(self.interface.cvars['rpms-directory'], name='%s-*-*' %(pkgname,),
                nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]')
    if len(rpms) == 0:
      rpms = find(self.interface.cvars['rpms-directory'], name='*-logos-*-*',
                  nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]')
      if len(rpms) == 0:
        raise RpmNotFoundError("missing logo RPM")
    return [rpms[0]]


class InstallerReleaseHook(ExtractEventHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.rpmextract.installer-release-files'

    self.metadata_struct = {
      'config': ['//installer/release-files'],
    }
    
    ExtractEventHandler.__init__(self, interface, self.metadata_struct,
                                 join(interface.METADATA_DIR, 'installer-release-files.md'))
  
  def run(self):
    ExtractEventHandler.extract(self, "synchronizing installer release files")

  def generate(self):
    files = {}
    rtn = []    
    for path in self.config.xpath('//installer/release-files/path', []):
      source = path.text
      dest = join(self.software_store, path.attrib['dest'])
      files[source] = dest
    if self.config.get('//release-files/include-in-tree/@use-default-set', 'True') in BOOLEANS_TRUE:
      for default_item in ['eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README',
                           '*-RPM-GPG', 'RPM-GPG-KEY-*', 'RPM-GPG-KEY-beta',
                           'README-BURNING-ISOS-en_US.txt', 'RELEASE-NOTES-en_US.html']:
        for item in find(location=self.working_dir, name=default_item):    
          files[item] = self.software_store

    for source in files.keys():
      dest = files[source]
      if isfile(source) and isdir(dest):
        dest = join(dest, basename(source))
      rtn.append(dest)
      if exists(dest):
        rm(dest, force=True)
      os.link(source, dest)
    return rtn

  def find_rpms(self):
    rpmnames = self.config.xpath('//installer/release-files/package/text()',
                                ['%s-release' %(self.interface.product,)])
    rpms = []
    for rpmname in rpmnames:
      release_rpms = find(self.interface.cvars['rpms-directory'], name='%s-*-*' %(rpmname,),
                          nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]')
      rpms.extend(release_rpms)
    if len(rpms) == 0:
      for glob in ['*-release-*-[a-zA-Z0-9]*.[Rr][Pp][Mm]',
                   '*-release-notes-*-*']:
        release_rpms = find(self.interface.cvars['rpms-directory'], name=glob,
                            nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]')
        rpms.extend(release_rpms)
        if len(rpms) == 0:
          raise RpmNotFoundError("missing release RPM(s)")
    return rpms    

L_INSTALLER_LOGOS = '''
<locals>
  <installer-logos>

    <installer-logo version="0">
      <splash-image>
        <format>lss</format>
      </splash-image>
    </installer-logo>

    <installer-logo version="11.2.0.66-1">
      <action type="update" path="splash-image">
        <format>jpg</format>
      </action>
    </installer-logo>

  </installer-logos>
</locals>
'''

#------ EXCEPTIONS ------#
class RpmNotFoundError(Exception): pass
class SplashImageNotFound(StandardError): pass
