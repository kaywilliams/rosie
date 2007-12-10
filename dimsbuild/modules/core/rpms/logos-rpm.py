from dims import pps

from dimsbuild.event import Event

from dimsbuild.modules.shared import RpmBuildMixin

try:
  import Image
  import ImageDraw
  import ImageFont
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
      default_provides = ['system-logos']
    )

    self.DATA = {
      'config': ['.'],
      'variables': ['fullname', 'product', 'pva', 'rpm_release',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'base-vars\'][\'copyright\']',
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
    for image_file in self.logos_dir.findpaths(type=pps.constants.TYPE_NOT_DIR):
      basename = image_file.basename
      relpath = image_file.relpathfrom(self.logos_dir)

      if self.locals.logos_rpm.has_key(basename):
        file_dict = self.locals.logos_rpm[basename]
      else:
        file_dict = {}

      output_format = file_dict.get('output_format', None)
      output_locations = file_dict.get('output_locations', ['/%s' % relpath])
      text_string = file_dict.get('text', '') % self.cvars['base-vars']
      text_coords = file_dict.get('text_coords', None)
      font_color  = file_dict.get('font_color', 'black')
      font_size   = file_dict.get('font_size', None)

      if basename == 'COPYING':
        ## HACK: special-casing COPYING; find a better way to do this
        self.copy(image_file, self.build_folder)
      else:
        for output_location in [ P(x) for x in output_locations ] :
          dest = self.build_folder // output_location
          dest.dirname.mkdirs()
          if text_string:
            self._generate_image(image_file, dest, text_string, font_size,
                                 format=output_format, text_coords=text_coords,
                                 font_color=font_color)
          elif output_format is not None:
            Image.open(image_file).save(dest, format=output_format)
          else:
            self.copy(image_file, dest.dirname)

          self.data_files.setdefault(output_location.dirname, []).append(
            dest.relpathfrom(self.build_folder)
          )

  def _generate_image(self, start_file, end_file, text, font_size,
                      format='png', text_coords=None, font_color='black'):
    im = Image.open(start_file)

    if text:
      if text_coords is None:
        width, height = im.size
        text_coords = (width/2, height/2)
      if font_size is None:
        font_size = 52

      draw, handler = ImageDraw.getdraw(im)
      font = handler.Font(font_color, self.font_file, size=font_size)
      w, h = draw.textsize(text, font)
      draw.text((text_coords[0]-(w/2), text_coords[1]-(h/2)), text, font)

    im.save(end_file, format=format)

  def _add_doc_files(self, spec):
    spec.set('bdist_rpm', 'doc_files', 'COPYING')
