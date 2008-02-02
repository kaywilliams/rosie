import gzip

from rendition import shlib
from rendition import pps

from spin.event import Event

from spin.modules.shared import RpmBuildMixin, ImagesGenerator

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['LogosRpmEvent']}

class LogosRpmEvent(RpmBuildMixin, Event, ImagesGenerator):
  def __init__(self):
    Event.__init__(self,
      id = 'logos-rpm',
      version = '0.9',
      requires = ['base-info', 'anaconda-version', 'logos-versions'],
      provides = ['custom-rpms-data']
    )

    RpmBuildMixin.__init__(self,
      '%s-logos' % self.product,
      "The %s-logos package contains image files which have been automatically "
      "created by spin and are specific to %s." % (self.product, self.fullname),
      "Icons and pictures related to %s" % self.fullname,
      rpm_license = 'GPLv2',
      default_provides = ['system-logos']
    )

    ImagesGenerator.__init__(self)

    self.DATA = {
      'config': ['.'],
      'variables': ['pva', 'fullname', 'copyright', 'rpm_release',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'logos-versions\']'],
      'output': [self.build_folder],
      'input':  [],
    }

  def setup(self):
    obsoletes = [ '%s %s %s' %(n,e,v)
                  for n,e,v in self.cvars.get('logos-versions', [])]
    provides = [ 'system-logos %s %s' % (e,v)
                 for _,e,v in self.cvars.get('logos-versions', [])]
    self._setup_build(obsoletes=obsoletes, provides=provides)
    self._setup_image_creation('logos')

  def _generate(self):
    RpmBuildMixin._generate(self)
    self._create_dynamic_images(self.locals.logos_files)
    self._copy_static_images()
    self._create_grub_splash_xpm()

  def _create_grub_splash_xpm(self):
    # HACK: to create the splash.xpm file, have to first convert
    # the grub-splash.png to an xpm and then gzip it.
    splash_xpm = self.build_folder / 'boot/grub/grub-splash.xpm'
    splash_xgz = self.build_folder / 'boot/grub/grub-splash.xpm.gz'
    splash_png = self.build_folder / 'boot/grub/grub-splash.png'
    shlib.execute('convert %s %s' %(splash_png, splash_xpm))
    infile = file(splash_xpm, 'rb')
    data = infile.read()
    infile.close()
    outfile = gzip.GzipFile(splash_xgz, 'wb')
    outfile.write(data)
    outfile.close()
