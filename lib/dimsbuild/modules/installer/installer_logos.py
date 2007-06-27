from os.path import exists, join

try:
  import Image
except ImportError:
  raise ImportError("missing 'python-imaging' RPM")

from dims import shlib

from dims.osutils import *
from dims.sync    import sync

from dimsbuild.event import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.magic import FILE_TYPE_JPG, FILE_TYPE_LSS, match as magic_match
from dimsbuild.misc  import locals_imerge

from lib import ExtractHandler, RpmNotFoundError

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'installer-logos',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['installer-splash'],
    'requires': ['software'],
    'conditional-requires': ['gpgsign'],    
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'InstallerLogosHook': 'installer-logos',
  'ValidateHook':       'validate',
}

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer_logos.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('//installer/logos', schemafile='installer-logos.rng')

class InstallerLogosHook(ExtractHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer_logos.installer-logos'

    self.metadata_struct = {
      'config'   : ['//installer/logos'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input'    : [],
      'output'   : [],
    }
    
    ExtractHandler.__init__(self, interface, self.metadata_struct,
                            join(interface.METADATA_DIR, 'installer-logos.md'))
  
  def setup(self):
    self.locals = locals_imerge(L_INSTALLER_LOGOS, self.interface.cvars['anaconda-version'])
    self.format = self.locals.get('//splash-image/format/text()')
    self.file = self.locals.get('//splash-image/file/text()')
  
  def check(self):
    return ExtractHandler.check(self)
  
  def run(self):
    ExtractHandler.extract(self, "processing installer logos")

  def generate(self):
    "Create the splash image and copy it to the isolinux/ folder"
    output_dir = join(self.software_store, 'isolinux')
    if not exists(output_dir):
      mkdir(output_dir, parent=True)

    # copy images to the product.img/ folder
    output = self.copy_pixmaps()

    # create the splash image
    output.append(self.generate_splash())
    
    return output
  
  def generate_splash(self):
    splash = join(self.software_store, 'isolinux', 'splash.%s' %self.format)
    # convert the syslinux-splash.png to splash.lss and copy it
    # to the isolinux/ folder
    try:
      startimage = find(self.working_dir, self.file)[0]
    except IndexError:
      raise SplashImageNotFound("missing '%s' in logos RPM" %(self.file,))

    if self.format == 'jpg':
      cp(startimage, splash)
    else:
      shlib.execute('pngtopnm %s | ppmtolss16 \#cdcfd5=7 \#ffffff=1 \#000000=0 \#c90000=15 > %s'
                    %(startimage, splash,))
    return splash

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
      for image in find(folder, type=TYPE_FILE|TYPE_LINK, prefix=True):
        file_name = basename(image)
        self.interface.log(4, "hardlinking %s to %s" %(file_name, product_img,))
        pixmap = join(product_img, file_name)
        sync(image, product_img, link=True)
        pixmaps.append(pixmap)
    return pixmaps

  def apply(self):
    splash = join(self.software_store, 'isolinux', 'splash.%s' %self.format)
    if not exists(splash):
      raise RuntimeError("missing file: '%s'" %(splash))
    if not self.valid_splash(splash):
      raise RuntimeError("%s is not a valid %s file" %(splash, self.format))
    self.interface.cvars['installer-splash'] = splash

  def valid_splash(self, splash):
    if self.format == 'jpg':
      return magic_match(splash) == FILE_TYPE_JPG
    else:
      return magic_match(splash) == FILE_TYPE_LSS
      
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


L_INSTALLER_LOGOS = ''' 
<locals>
  <installer-logos>

    <installer-logo version="0">
      <splash-image>
        <format>lss</format>
        <file>syslinux-splash.png</file>
      </splash-image>
    </installer-logo>

    <installer-logo version="11.2.0.66-1">
      <action type="update" path="splash-image">
        <format>jpg</format>
        <file>syslinux-vesa-splash.jpg</file>
      </action>
    </installer-logo>

  </installer-logos>
</locals>
'''

#------ EXCEPTIONS ------#
class SplashImageNotFound(StandardError): pass
