from os.path import exists, join

from dims import osutils
from dims import shlib

from dimsbuild.event import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.magic import FILE_TYPE_JPG, FILE_TYPE_LSS, match as magic_match
from dimsbuild.misc  import locals_imerge

from lib import ExtractMixin, RpmNotFoundError

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'logos',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['installer-splash'],
    'requires': ['software', 'anaconda-version'],
    'conditional-requires': ['gpgsign'],    
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'LogosHook':    'logos',
  'ValidateHook': 'validate',
}

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'logos.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/installer/logos',
                            schemafile='logos.rng')
    

class LogosHook(ExtractMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'logos.logos'

    self.metadata_struct = {
      'config'   : ['/distro/installer/logos'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input'    : [],
      'output'   : [],
    }
    
    ExtractMixin.__init__(self, interface, self.metadata_struct,
                          join(interface.METADATA_DIR, 'INSTALLER', 'logos.md'))
  
  def setup(self):
    self.locals = locals_imerge(L_LOGOS, self.interface.cvars['anaconda-version'])
    self.format = self.locals.get('//splash-image/format/text()')
    self.file = self.locals.get('//splash-image/file/text()')
    self.DATA['input'].extend(self.find_rpms())
    self.interface.setup_diff(self.mdfile, self.DATA)

  def clean(self):
    self.interface.log(0, "cleaning logos event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "processing logos")
    self.extract()

  def generate(self, working_dir):
    "Create the splash image and copy it to the isolinux/ folder"
    output_dir = join(self.software_store, 'isolinux')
    if not exists(output_dir):
      osutils.mkdir(output_dir, parent=True)

    # copy images to the product.img/ folder
    output = self.copy_pixmaps(working_dir)

    # create the splash image
    output.append(self.generate_splash(working_dir))
    
    return output
  
  def generate_splash(self, working_dir):
    splash = join(self.software_store, 'isolinux/splash.%s' %self.format)
    # convert the syslinux-splash.png to splash.lss and copy it
    # to the isolinux/ folder
    try:
      startimage = osutils.find(working_dir, name=self.file)[0]
    except IndexError:
      raise SplashImageNotFound("missing '%s' in logos RPM" %(self.file,))

    if self.format == 'jpg':
      osutils.cp(startimage, splash)
    else:
      shlib.execute('pngtopnm %s | ppmtolss16 \#cdcfd5=7 \#ffffff=1 \#000000=0 \#c90000=15 > %s'
                    %(startimage, splash,))
    return splash

  def copy_pixmaps(self, working_dir):
    """ 
    Create the product.img folder that can be used by the product.img
    module.
    """
    # link the images from the RPM folder to the pixmaps/ folder in
    # the folder the product.img event looks in.
    product_img = join(self.interface.METADATA_DIR, 'images-src/product.img/pixmaps')
    osutils.mkdir(product_img, parent=True)
    
    # generate the list of files to use and copy them to the
    # product.img folder
    pixmaps = []
    for img in osutils.find(working_dir,
                            regex='.*usr/share/anaconda/pixmaps*',
                            type=osutils.TYPE_FILE|osutils.TYPE_LINK):
      self.interface.copy(img, product_img)
      pixmaps.append(join(product_img, osutils.basename(img)))
    return pixmaps

  def apply(self):
    splash = join(self.software_store, 'isolinux/splash.%s' %self.format)
    if not exists(splash):
      raise RuntimeError("missing file: '%s'" %(splash))
    if not self.validate_splash(splash):
      raise RuntimeError("'%s' is not a valid '%s' file" %(splash, self.format))
    self.interface.cvars['installer-splash'] = splash

  def validate_splash(self, splash):
    if self.format == 'jpg':
      return magic_match(splash) == FILE_TYPE_JPG
    else:
      return magic_match(splash) == FILE_TYPE_LSS
      
  def find_rpms(self):
    pkgname = self.config.get('/distro/installer/logos/package/text()',
                              '%s-logos' %(self.interface.product,))    
    rpms = osutils.find(self.interface.cvars['rpms-directory'], name='%s-*-*' %(pkgname,),
                        nregex='.*[Ss][Rr][Cc]\.[Rr][Pp][Mm]')
    if len(rpms) == 0:
      rpms = osutils.find(self.interface.cvars['rpms-directory'], name='*-logos-*-*',
                          nregex='.*[Ss][Rr][Cc]\.[Rr][Pp][Mm]')
      if len(rpms) == 0:
        raise RpmNotFoundError("missing logo RPM")
    return [rpms[0]]


L_LOGOS = ''' 
<locals>
  <logos>

    <logo version="0">
      <splash-image>
        <format>lss</format>
        <file>syslinux-splash.png</file>
      </splash-image>
    </logo>

    <!-- approx 11.2.0.66-1 - started using a .jpg instead of converting -->
    <!-- syslinux.png to splash.lss                                      -->
    <logo version="11.2.0.66-1">
      <action type="update" path="splash-image">
        <format>jpg</format>
        <file>syslinux-vesa-splash.jpg</file>
      </action>
    </logo>

  </logos>
</locals>
'''

#------ EXCEPTIONS ------#
class SplashImageNotFound(StandardError): pass
