from rendition import pps

from spin.event import Event

from spin.modules.shared import RpmBuildMixin, ImagesCreator

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['LogosRpmEvent']}

class LogosRpmEvent(Event, RpmBuildMixin, ImagesCreator):
  def __init__(self):
    Event.__init__(self,
      id = 'logos-rpm',
      version = 6,
      requires = ['source-vars', 'anaconda-version', 'logos-versions'],
      provides = ['custom-rpms', 'custom-srpms', 'custom-rpms-info']
    )

    RpmBuildMixin.__init__(self,
      '%s-logos' % self.product,
      "The %s-logos package contains image files which have been automatically "
      "created by spin and are specific to %s." % (self.product, self.fullname),
      "Icons and pictures related to %s" % self.fullname,
      rpm_license = 'GPLv2',
      default_provides = ['system-logos']
    )

    ImagesCreator.__init__(self)

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
    RpmBuildMixin._generate(self)
    self.create_images(self.locals.logos_files)
    self.copy_images('logos')

  def _get_font_path(self, font):
    """
    Given a font file name, returns the full path to the font located in one
    of the share directories
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
