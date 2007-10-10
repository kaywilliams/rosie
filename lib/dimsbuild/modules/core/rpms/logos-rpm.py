from dims import pps
from dims import shlib

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event
from dimsbuild.logging   import L3

from dimsbuild.modules.shared.rpms import ColorMixin, LocalFilesMixin, RpmBuildMixin

try:
  import Image
  import ImageDraw
  import ImageFont
  import ImageFilter
except ImportError:
  raise ImportError("missing 'python-imaging' RPM")

P = pps.Path

API_VERSION = 5.0

class LogosRpmEvent(Event, RpmBuildMixin, ColorMixin, LocalFilesMixin):
  def __init__(self):
    Event.__init__(self, id='logos-rpm',
                   requires=['source-vars', 'anaconda-version'],
                   provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info'])
    RpmBuildMixin.__init__(self,
                           '%s-logos' % self.product,
                           'The %s-logos package contains image files which '\
                           'have been automatically created by dimsbuild and '\
                           'are specific to %s.' % (self.product, self.fullname),
                           'Icons and pictures related to %s' % self.fullname,
                           defobsoletes='fedora-logos centos-logos redhat-logos',
                           defprovides='system-logos')
    LocalFilesMixin.__init__(self)
    ColorMixin.__init__(self)

    self.fileslocals = self.locals.logos_rpm
    self.DATA = {
      'config': ['.'],
      'variables': ['fullname', 'product', 'pva'],
      'output': [],
      'input':  [],
    }

  def setup(self):
    self._setup_build()
    self._setup_locals()

    # set the font to use
    available_fonts = (self.SHARE_DIR/'fonts').findpaths(glob='*.ttf')
    try:
      self.fontfile = available_fonts[0]
    except IndexError:
      raise RuntimeError("Unable to find any font files in share path '%s'" % self.SHARE_DIR)

    # convert the colors to big endian because the python-imaging
    # library uses big-endian colors.
    self.setColors(be=True)
    self.bgcolor = int(self.bgcolor, 16)
    self.textcolor = int(self.textcolor, 16)
    self.hlcolor = int(self.hlcolor, 16)

  def check(self):
    return self.release == '0' or \
           not self.autofile.exists() or \
           self.diff.test_diffs()

  def run(self):
    self.io.clean_eventcache(all=True)
    if self._test_build('True'):
      self._build_rpm()
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    if not self._test_build('True'):
      return
    self._check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []
    self.cvars['custom-rpms-info'].append((self.rpmname, 'mandatory', None, self.obsoletes))

  def _get_files(self):
    sources = {}
    sources.update(RpmBuildMixin._get_files(self))
    sources.update(LocalFilesMixin._get_files(self))
    return sources

  def _generate(self):
    self._generate_images()
    self._generate_theme_files()

  def _generate_theme_files(self):
    # generate the theme.xml file
    f = (self.build_folder/'gdm/themes' / \
         self.product/'%s.xml' % self.product).open('w')
    f.write(self.locals.theme_xml)
    f.close()

    # generate the GdmGreeterTheme.desktop file
    f = (self.build_folder/'gdm/themes' / \
         self.product/'GdmGreeterTheme.desktop').open('w')
    f.write(self.locals.gdm_greeter % self.cvars['base-vars'])
    f.close()

  def _generate_images(self):
    for id in self.fileslocals.keys():
      locations = self.fileslocals[id]['locations']

      width  = self.fileslocals[id].get('width', None)
      height = self.fileslocals[id].get('height', None)

      maxwidth = self.fileslocals[id].get('textmaxwidth', None)
      vcenter  = self.fileslocals[id].get('textvcenter', None)
      hcenter  = self.fileslocals[id].get('texthcenter', None)

      format = self.fileslocals[id].get('format', 'png')

      filename = self.build_folder/id
      destdir  = filename.dirname
      if not destdir.isdir(): destdir.mkdirs()

      sharedfile = self.SHARE_DIR/'logos'/id
      if sharedfile.exists():
        self.log(4, L3("file '%s' exists in share/" % id))
        self.copy(sharedfile, destdir)
      elif width and height:
        self.log(4, L3("creating '%s'" % id))
        if maxwidth and vcenter and hcenter:
          self._generate_image(filename, width, height,
                               text='%s %s' % (self.fullname, self.version),
                               textcood=(hcenter, vcenter),
                               maxwidth=maxwidth,
                               format=format)
        else:
          self._generate_blank_image(filename, width, height, format=format)

    # HACK: to create the splash.xpm file, have to first convert
    # the grub-splash.png to an xpm and then gzip it.
    splash_xpm = self.build_folder/'bootloader/grub-splash.xpm'
    splash_xgz = splash_xpm + '.gz'
    if not splash_xgz.exists():
      splash_png = self.build_folder/'bootloader/grub-splash.png'

      # TODO: Find a better way to do this conversion.
      shlib.execute('convert %s %s' %(splash_png, splash_xpm,))
      import gzip
      infile = file(splash_xpm, 'rb')
      data = infile.read()
      infile.close()
      outfile = gzip.GzipFile(splash_xgz, 'wb')
      outfile.write(data)
      outfile.close()

  def _generate_image(self, filename, width, height, text=None,
                      textcood=(10,10), fontsize=52, maxwidth=100,
                      format='png', font=None,
                      highlight=False, gradient=False):
    """
    Generate an image that is added to the logos RPM and the product.img.

    TODO: add support for the gradient parameter.

    @param filename   : the name of the file to be generated
    @param width      : the width of the image
    @param height     : the height of the image
    @param text       : the text to be added to the image
    @param textcood   : coordinates of the center of the text block
    @param fontsize   : the 'starting' font size of the text on the image
    @param maxwidth   : maximum length of the text block
    @param format     : the format of the image: png, jpeg etc.
    """
    def getfont(fontsize, fontfile):
      xcood, ycood = textcood
      startX = xcood - maxwidth/2
      font = ImageFont.truetype(fontfile, fontsize)
      (textwidth, textheight) = font.getsize(text)
      startY = ycood - textheight/2
      while (textwidth > maxwidth) or \
                ((startX+textwidth) > width) or \
                ((startY+textheight) > height):
        if textheight <= 10:
          return None # if fontsize is less than 10, don't write anything
        fontsize = fontsize - 2
        font = ImageFont.truetype(fontfile, fontsize)
        (textwidth, textheight) = font.getsize(text)
        startY = ycood - textheight/2
      return font

    if highlight:
      color = self.hlcolor
    else:
      color = self.bgcolor
    im = Image.new('RGB', (width, height), color)

    # add text to the image, if specified
    if text:
      if font is None:
        font = getfont(fontsize, self.fontfile)
      # if font is None, the text is too long for the image, don't
      # write anything as it will look ugly.
      if font is not None:
        d = ImageDraw.Draw(im)
        w, h = font.getsize(text)
        d.text((textcood[0]-(w/2), textcood[1]-(h/2)), text,
               font=font, fill=self.textcolor)

    # save the image to a file
    im = im.filter(ImageFilter.DETAIL)
    im.save(filename, format=format)

  _generate_blank_image = _generate_image


EVENTS = {'rpms': [LogosRpmEvent]}
