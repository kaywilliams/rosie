#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
from rendition import magic
from rendition import pps
from rendition import shlib

from spin.constants import SRPM_REGEX
from spin.event     import Event

from spin.modules.shared import ExtractMixin, RpmNotFoundError

API_VERSION = 5.0
EVENTS = {'installer': ['LogosEvent']}

class LogosEvent(Event, ExtractMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'logos',
      provides = ['isolinux-files', 'product-image-content'],
      requires = ['rpms-directory', 'anaconda-version'],
      conditionally_comes_after = ['gpgsign'],
    )

    self.DATA = {
      'config'   : ['.'],
      'variables': ['name', 'cvars[\'anaconda-version\']'],
      'input'    : [],
      'output'   : [],
    }

    self.dorun = True # whether to run or not

  def setup(self):
    self.format   = self.locals.L_LOGOS['splash-image']['format']
    self.filename = self.locals.L_LOGOS['splash-image']['filename']
    if self.locals.L_LOGOS['splash-image'].has_key('output'):
      self.splash = self.SOFTWARE_STORE/'isolinux/%s' % \
                    self.locals.L_LOGOS['splash-image']['output']
    else:
      self.splash = self.SOFTWARE_STORE/'isolinux/splash.%s' % self.format
    rpm = self._find_rpms()
    if not rpm:
      self.dorun = False
    else:
      self.DATA['input'].extend(rpm)
    self.diff.setup(self.DATA)

  def check(self):
    return self.dorun and Event.check(self)

  def run(self):
    self._extract()

  def apply(self):
    self.io.clean_eventcache()

    self.cvars.setdefault('isolinux-files', {})
    self.cvars['isolinux-files']['installer-splash'] = self.splash
    if (self.mddir/'pixmaps').exists(): # caught by verification
      self.cvars['product-image-content'].setdefault('/pixmaps', set()).update(
        (self.mddir/'pixmaps').listdir())

  #def verify_splash_exists(self):
  #  "splash image exists"
  #  self.verifier.failUnlessExists(self.splash)

  #def verify_splash_valid(self):
  #  "splash image is valid"
  #  self.verifier.failUnless(self._validate_splash(),
  #    "'%s' is not a valid %s file" % (self.splash, self.format))

  #def verify_pixmaps_exist(self):
  #  "pixmaps folder populated"
  #  self.verifier.failUnlessExists(self.mddir/'pixmaps')

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
    dirs = ['/usr/share/anaconda/pixmaps']
    for dir in [ working_dir // dir for dir in dirs ]:
      for src in dir.findpaths(type=pps.constants.TYPE_NOT_DIR):
        dst = product_img / src.relpathfrom(dir)
        dst.dirname.mkdirs()
        self.link(src, dst.dirname)
        pixmaps.append(dst)
    return pixmaps

  def _validate_splash(self):
    if self.format == 'jpg':
      return magic.match(self.splash) == magic.FILE_TYPE_JPG
    elif self.format == 'png':
      return magic.match(self.splash) == magic.FILE_TYPE_PNG
    else:
      return magic.match(self.splash) == magic.FILE_TYPE_LSS

  def _find_rpms(self):
    pkgname = self.config.get('package/text()', '%s-logos' % self.name)
    rpms = self.cvars['rpms-directory'].findpaths(
      glob='%s-*-*' % pkgname, nregex=SRPM_REGEX)
    if len(rpms) == 0:
      rpms = self.cvars['rpms-directory'].findpaths(
        glob='*-logos-*-*', nregex=SRPM_REGEX)
      if len(rpms) == 0:
        return None
    return [rpms[0]]


#------ EXCEPTIONS ------#
class SplashImageNotFound(StandardError): pass
