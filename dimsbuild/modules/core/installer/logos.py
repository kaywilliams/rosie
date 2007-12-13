from dims import magic
from dims import pps
from dims import shlib

from dimsbuild.constants import SRPM_REGEX
from dimsbuild.event     import Event

from dimsbuild.modules.shared import ExtractMixin, RpmNotFoundError

P = pps.Path

API_VERSION = 5.0
EVENTS = {'installer': ['LogosEvent']}

class LogosEvent(Event, ExtractMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'logos',
      provides = ['installer-splash', 'product-image-content'],
      requires = ['rpms-directory', 'anaconda-version'],
      conditionally_comes_after = ['gpgsign'],
    )

    self.DATA = {
      'config'   : ['.'],
      'variables': ['product', 'cvars[\'anaconda-version\']'],
      'input'    : [],
      'output'   : [],
    }

  def setup(self):
    self.format = self.locals.logos['splash-image']['format']
    self.filename = self.locals.logos['splash-image']['filename']
    if self.locals.logos['splash-image'].has_key('output'):
      self.splash = self.SOFTWARE_STORE/'isolinux/%s' % \
                    self.locals.logos['splash-image']['output']
    else:
      self.splash = self.SOFTWARE_STORE/'isolinux/splash.%s' % self.format
    self.DATA['input'].extend(self._find_rpms())
    self.diff.setup(self.DATA)

  def run(self):
    self._extract()

  def apply(self):
    self.io.clean_eventcache()

    self.cvars['installer-splash'] = self.splash
    if (self.mddir/'pixmaps').exists(): # caught by verification
      self.cvars['product-image-content'].setdefault('/pixmaps', set()).update(
        (self.mddir/'pixmaps').listdir())

  def verify_splash_exists(self):
    "splash image exists"
    self.verifier.failUnlessExists(self.splash)

  def verify_splash_valid(self):
    "splash image is valid"
    self.verifier.failUnless(self._validate_splash(),
      "'%s' is not a valid %s file" % (self.splash, self.format))

  def verify_pixmaps_exist(self):
    "pixmaps folder populated"
    self.verifier.failUnlessExists(self.mddir/'pixmaps')

  def _generate(self, working_dir):
    "Create the splash image and copy it to the isolinux/ folder"
    output_dir = self.SOFTWARE_STORE/'isolinux'
    if not output_dir.exists():
      output_dir.mkdirs()

    # copy images to the product.img/ folder
    output = self._copy_pixmaps(working_dir)

    # create the splash image
    self._generate_splash(working_dir)
    output.append(self.splash)

    return output

  def _generate_splash(self, working_dir):
    # convert the syslinux-splash.png to splash.lss and copy it
    # to the isolinux/ folder
    try:
      startimage = working_dir.findpaths(glob=self.filename)[0]
    except IndexError:
      raise SplashImageNotFound("missing '%s' in logos RPM" % self.filename)

    if self.format == 'lss':
      shlib.execute('pngtopnm %s | ppmtolss16 \#cdcfd5=7 \#ffffff=1 \#000000=0 \#c90000=15 > %s'
                    %(startimage, self.splash))
    else:
      startimage.cp(self.splash)

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
      self.link(img, product_img)
      outfile = product_img/img.basename
      pixmaps.append(outfile)

    return pixmaps

  def _validate_splash(self):
    if self.format == 'jpg':
      return magic.match(self.splash) == magic.FILE_TYPE_JPG
    elif self.format == 'png':
      return magic.match(self.splash) == magic.FILE_TYPE_PNG
    else:
      return magic.match(self.splash) == magic.FILE_TYPE_LSS

  def _find_rpms(self):
    pkgname = self.config.get('package/text()', '%s-logos' % self.product)
    rpms = P(self.cvars['rpms-directory']).findpaths(
      glob='%s-*-*' % pkgname, nregex=SRPM_REGEX)
    if len(rpms) == 0:
      rpms = P(self.cvars['rpms-directory']).findpaths(
        glob='*-logos-*-*', nregex=SRPM_REGEX)
      if len(rpms) == 0:
        raise RpmNotFoundError("missing logo RPM")
    return [rpms[0]]


#------ EXCEPTIONS ------#
class SplashImageNotFound(StandardError): pass
