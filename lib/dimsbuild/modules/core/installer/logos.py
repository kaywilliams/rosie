from dims import pps
from dims import shlib

from dimsbuild.constants import SRPM_REGEX
from dimsbuild.event     import Event
from dimsbuild.logging   import L0
from dimsbuild.magic     import FILE_TYPE_JPG, FILE_TYPE_LSS, match as magic_match

from dimsbuild.modules.shared.installer import ExtractMixin, RpmNotFoundError

P = pps.Path

API_VERSION = 5.0

class LogosEvent(Event, ExtractMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'logos',
      provides = ['installer-splash', 'product-image-content'],
      requires = ['rpms-directory', 'anaconda-version'],
      conditionally_comes_after = ['gpgsign'],
    )
    
    self.DATA = {
      'config'   : ['/distro/logos'],
      'variables': ['product', 'cvars[\'anaconda-version\']'],
      'input'    : [],
      'output'   : [],
    }
    
  def validate(self):
    self.validator.validate('/distro/logos', 'logos.rng')
  
  def setup(self):
    self.format = self.locals.logos['splash-image']['format']
    self.filename = self.locals.logos['splash-image']['filename']
    self.DATA['input'].extend(self._find_rpms())
    self.diff.setup(self.DATA)
    
  def run(self):
    self.log(0, L0("embedding distribution-specific branding images into installer"))
    self._extract()
  
  def apply(self):
    self.io.clean_eventcache()
    splash = self.SOFTWARE_STORE/'isolinux/splash.%s' % self.format
    if not splash.exists():
      raise RuntimeError("missing file: '%s'" % splash)
    if not self._validate_splash(splash):
      raise RuntimeError("'%s' is not a valid '%s' file" %(splash, self.format))
    self.cvars['installer-splash'] = splash
    
    self.cvars['product-image-content'].setdefault('/pixmaps', set()).update(
      (self.mddir/'pixmaps').listdir())

  def _generate(self, working_dir):
    "Create the splash image and copy it to the isolinux/ folder"
    output_dir = self.SOFTWARE_STORE/'isolinux'
    if not output_dir.exists():
      output_dir.mkdirs()
    
    # copy images to the product.img/ folder
    output = self._copy_pixmaps(working_dir)
    
    # create the splash image
    output.append(self._generate_splash(working_dir))
    
    return output
  
  def _generate_splash(self, working_dir):
    splash = self.SOFTWARE_STORE/'isolinux/splash.%s' % self.format
    # convert the syslinux-splash.png to splash.lss and copy it
    # to the isolinux/ folder
    try:
      startimage = working_dir.findpaths(glob=self.filename)[0]
    except IndexError:
      raise SplashImageNotFound("missing '%s' in logos RPM" % self.filename)
    
    if self.format == 'jpg':
      startimage.cp(splash)
    else:
      shlib.execute('pngtopnm %s | ppmtolss16 \#cdcfd5=7 \#ffffff=1 \#000000=0 \#c90000=15 > %s'
                    %(startimage, splash,))
    return splash
  
  def _copy_pixmaps(self, working_dir):
    """ 
    Create the product.img folder that can be used by the product.img
    module.
    """
    # link the images from the RPM folder to the pixmaps/ folder 
    product_img = self.mddir/'pixmaps'
    product_img.mkdirs()
    
    # generate the list of files to use and copy them to the
    # product.img folder
    pixmaps = []
    for img in working_dir.findpaths(regex='.*usr/share/anaconda/pixmaps*',
                                     type=pps.constants.TYPE_NOT_DIR):
      img.cp(product_img, link=True)
      outfile = product_img/img.basename
      pixmaps.append(outfile)
    
    return pixmaps
  
  def _validate_splash(self, splash):
    if self.format == 'jpg':
      return magic_match(splash) == FILE_TYPE_JPG
    else:
      return magic_match(splash) == FILE_TYPE_LSS
      
  def _find_rpms(self):
    pkgname = self.config.get('/distro/logos/package/text()',
                              '%s-logos' %(self.product,))
    rpms = P(self.cvars['rpms-directory']).findpaths(
      glob='%s-*-*' % pkgname, nregex=SRPM_REGEX)
    if len(rpms) == 0:
      rpms = P(self.cvars['rpms-directory']).findpaths(
        glob='*-logos-*-*', nregex=SRPM_REGEX)
      if len(rpms) == 0:
        raise RpmNotFoundError("missing logo RPM")
    return [rpms[0]]


EVENTS = {'INSTALLER': [LogosEvent]}

#------ EXCEPTIONS ------#
class SplashImageNotFound(StandardError): pass
