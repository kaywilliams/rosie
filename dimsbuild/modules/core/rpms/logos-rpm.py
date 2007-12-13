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
      version = 5,
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
      'variables': ['pva', 'fullname', 'copyright', 'rpm_release',
                    'cvars[\'anaconda-version\']',],
      'output': [self.build_folder],
      'input':  [],
    }

  def setup(self):
    obsoletes = [ '%s %s %s' %(n,e,v)
                  for n,e,v in self.cvars.get('logos-versions', [])]
    provides = [ 'system-logos %s %s' % (e,v)
                 for _,e,v in self.cvars.get('logos-versions', [])]
    self._setup_build(obsoletes=obsoletes, provides=provides)

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
      strings = file_dict.get('strings', None)

      if basename == 'COPYING':
        ## HACK: special-casing COPYING; find a better way to do this
        self.copy(image_file, self.build_folder)
      else:
        for output_location in [ P(x) for x in output_locations ] :
          dest = self.build_folder // output_location
          dest.dirname.mkdirs()
          if strings:
            im = Image.open(image_file)
            for i in strings:
              text_string    = i.get('text', '') % self.cvars['base-vars']
              halign         = i.get('halign', 'center')
              text_coords    = i.get('text_coords', None)
              text_max_width = i.get('text_max_width', None)
              font_color     = i.get('font_color', 'black')
              font_size      = i.get('font_size', None)
              font_size_min  = i.get('font_size_min', None)
              font_path      = self._get_font_path(i.get('font', 
                                                         'DejaVuLGCSans.ttf'))

              self._generate_image(im, text_string, halign, font_size, 
                                   font_size_min, font_path, text_coords,
                                   text_max_width, font_color)

            im.save(dest, format=(output_format or 'png'))

          elif output_format is not None:
            Image.open(image_file).save(dest, format=output_format)
          else:
            self.copy(image_file, dest.dirname)

          self.data_files.setdefault(output_location.dirname, []).append(
            dest.relpathfrom(self.build_folder)
          )

  def _get_font_path(self, font):
    """
    Given a font file name, returns the full path to the font located in one
    of the share directories"
    """
    for path in self.SHARE_DIRS:
      available_fonts = (path/'fonts').findpaths(glob=font)
      if available_fonts:
        font_path = available_fonts[0]; break
      if not font_path:
        raise RuntimeError("Unable to find font file '%s' in share path(s) "
                           "'%s'" %  font_path, self.SHARE_DIRS)

    return font_path

  def _generate_image(self, im, text, halign, font_size, font_size_min, font_path,
                      text_coords, text_max_width, font_color):

    if text_coords is None:
      width, height = im.size
      text_coords = (width/2, height/2)
    if font_size is None:
      font_size = 52

    draw, handler = ImageDraw.getdraw(im)
    while font_size >= (font_size_min or font_size):
      font = handler.Font(font_color, font_path, size=font_size)
      w, h = draw.textsize(text, font)
      if w <= (text_max_width or im.size[0]):
        break
      else:
        font_size -= 1

    if halign == 'center':
      draw.text((text_coords[0]-(w/2), text_coords[1]-(h/2)), text, font)
    elif halign == 'right':
      draw.text((text_coords[0]-w, text_coords[1]-(h/2)), text, font)

    return im

  def _add_doc_files(self, spec):
    spec.set('bdist_rpm', 'doc_files', 'COPYING')
