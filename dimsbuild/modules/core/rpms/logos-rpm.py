from dims import pps

from dimsbuild.event import Event

from dimsbuild.modules.shared import RpmBuildMixin

try:
  import Image
  import ImageDraw
  import ImageFont
  import ImageFilter
except ImportError:
  raise ImportError("missing 'python-imaging' RPM")

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['LogosRpmEvent']}

class LogosRpmEvent(Event, RpmBuildMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'logos-rpm',
      version = 3,
      requires = ['source-vars', 'anaconda-version', 'logos-versions'],
      provides = ['custom-rpms', 'custom-srpms', 'custom-rpms-info']
    )

    RpmBuildMixin.__init__(self,
      '%s-logos' % self.product,
      "The %s-logos package contains image files which have been automatically "
      "created by dimsbuild and are specific to %s." % (self.product, self.fullname),
      "Icons and pictures related to %s" % self.fullname,
      rpm_license = 'GPLv2',
      default_obsoletes = ['fedora-logos', 'centos-logos', 'redhat-logos'],
      default_provides = ['system-logos']
    )

    self.DATA = {
      'config': ['.'],
      'variables': ['fullname', 'product', 'pva', 'rpm_release',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'base-vars\'][\'fullname\']',
                    'cvars[\'base-vars\'][\'version\']',],
      'output': [self.build_folder],
      'input':  [],
    }

  def setup(self):
    obsoletes = [ '%s %s %s' %(n,e,v)
                  for n,e,v in self.cvars.get('logos-versions', [])]
    provides = [ 'system-logos %s %s' % (e,v)
                 for _,e,v in self.cvars.get('logos-versions', [])]
    self._setup_build(obsoletes=obsoletes, provides=provides)

    # set the font to use
    self.font_file = None
    for path in self.SHARE_DIRS:
      available_fonts = (path/'fonts').findpaths(glob='*.ttf')
      if available_fonts:
        self.font_file = available_fonts[0]; break
    if not self.font_file:
      raise RuntimeError("Unable to find any font files in share path(s) '%s'" % \
                         self.SHARE_DIRS)

    # find the logos/ directory to use
    self.logos_dir = None
    for path in self.SHARE_DIRS:
      logos_dir = path / 'logos'
      if logos_dir.exists():
        self.logos_dir = logos_dir
    if self.logos_dir is None:
      raise RuntimeError("Unable to find logos/ directory in share path(s) '%s'" % \
                         self.SHARE_DIRS)

  def run(self):
    self.io.clean_eventcache(all=True)
    self._build_rpm()
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self._check_rpms()
    self.cvars.setdefault('custom-rpms-info', []).append(
      (self.rpm_name, 'mandatory', None, self.rpm_obsoletes, None)
    )

  def _generate(self):
    self._copy_images()

  def _copy_images(self):
    for image_file in self.logos_dir.findpaths(type=pps.constants.TYPE_NOT_DIR):
      basename = image_file.basename

      if self.locals.logos_rpm.has_key(basename):
        output_format = self.locals.logos_rpm[basename]['output_format']
        output_locations = self.locals.logos_rpm[basename]['output_locations']
        for output_location in [ P(x) for x in output_locations ] :
          install_dir = output_location.dirname
          file_name = self.build_folder // output_location
          file_name.dirname.mkdirs()
          Image.open(image_file).save(file_name, format=output_format)
          self.data_files.setdefault(install_dir, []).append(
            file_name.relpathfrom(self.build_folder)
          )
      else:
        relpath = image_file.relpathfrom(self.logos_dir)
        dest = self.build_folder // relpath
        install_dir = P('/%s' % relpath).dirname
        if basename == 'COPYING':
          ## HACK: find a better way to do this
          pass
        else:
          self.data_files.setdefault(install_dir, []).append(
            dest.relpathfrom(self.build_folder)
          )
        self.copy(image_file, dest.dirname)

  def _add_doc_files(self, spec):
    spec.set('bdist_rpm', 'doc_files', 'COPYING')
