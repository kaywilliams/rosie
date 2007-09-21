from dims import pps
from dims import shlib

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.logging   import L3

from dimsbuild.modules.rpms.lib    import ColorMixin, OutputInvalidError, RpmBuildEvent
from dimsbuild.modules.rpms.locals import L_LOGOS, GDM_GREETER_THEME, THEME_XML

try:
  import Image
  import ImageDraw
  import ImageFont
  import ImageFilter
except ImportError:
  raise ImportError("missing 'python-imaging' RPM")

P = pps.Path

API_VERSION = 5.0

class LogosRpmEvent(RpmBuildEvent, ColorMixin):
  def __init__(self):
    data = {
      'config': ['/distro/rpms/logos-rpm'],
      'variables': ['fullname', 'product'],
      'output': [],
      'input':  [],
    }
    
    RpmBuildEvent.__init__(self,
                           '%s-logos' % self.product,                           
                           'The %s-logos package contains image files which '\
                           'have been automatically created by dimsbuild and '\
                           'are specific to %s.' % (self.product, self.fullname),
                           'Icons and pictures related to %s' % self.fullname,
                           data,
                           defobsoletes='fedora-logos centos-logos redhat-logos',
                           defprovides='system-logos',
                           fileslocals=L_LOGOS % ((self.product,)*8),
                           id='logos-rpm',
                           requires=['source-vars', 'anaconda-version'])
    
    
  def validate(self):
    self.validator.validate('/distro/rpms/logos-rpm', 'logos-rpm.rng')
  
  def setup(self):
    RpmBuildEvent.setup(self)
    
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
  
  def run(self):
    self.remove_output(all=True)
    if not self._test_build('True'):
      return
    self._build_rpm()
    self._add_output()    
    self.write_metadata()    
  
  def apply(self):
    if not self._test_build('True'):
      return
    self._check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []      
    self.cvars['custom-rpms-info'].append((self.rpmname, 'mandatory', None, self.obsoletes))
  
  def _generate(self):
    self._generate_images()
    self._generate_theme_files()
    if not self._output_valid():
      raise OutputInvalidError      
  
  def _output_valid(self):
    if self.DATA.has_key('output'):
      for logoinfo in self.fileslocals.xpath('//files/file', []):
        i,_,w,h,_,_,_,_,_,_ = self._get_image_info(logoinfo)
        file = self.build_folder/i
        if file.lower().endswith('xpm'):
          # HACK: Assuming that all the .xpm files are valid. It is a fair
          # assumption because all the xpm files are from the shared directory
          continue
        if w and h:
          try:
            image = Image.open(file)
          except IOError:
            # should never happen
            self.errlog(4, L3("file '%s' was not found" % file))
            return False
          if image.size != (w,h):
            self.errlog(4, L3("file '%s' has invalid dimensions" % file))
            return False
    return True
  
  def _generate_theme_files(self):
    # generate the GdmGreeterTheme.desktop file
    f = (self.build_folder/'gdm/themes' / \
         self.product/'GdmGreeterTheme.desktop').open('w')
    f.write(GDM_GREETER_THEME %(self.product, self.fullname,
                                self.fullname,))
    f.close()
    # generate the %{self.product}.xml file
    f = (self.build_folder/'gdm/themes' / \
         self.product/'%s.xml' % self.product).open('w')
    f.write(THEME_XML)
    f.close()
  
  def _generate_images(self):
    for logoinfo in self.fileslocals.xpath('//files/file', []):
      # (id, _, location, width, height, maxwidth, x, y, gradient, highlight)
      i,_,l,b,m,x,y,g,h,f = self._get_image_info(logoinfo)
      sharedfile = self.SHARE_DIR/'logos'/i
      filename = self.build_folder/i
      dir = filename.dirname
      if filename.exists():
        filename.rm(force=True)
      if not dir.isdir():
        dir.mkdirs()
      
      if l and b:
        if sharedfile.exists():
          self.log(4, L3("image '%s' exists in share/" %i))
          self.copy(sharedfile, dir)
        else:
          self.log(4, L3("creating '%s'" %i))
          if m and x and y:
            self._generate_image(filename, l, b,
                                 text='%s %s ' %(self.fullname,
                                                 self.version),
                                 textcood=(x,y),
                                 fontsize=52,
                                 maxwidth=m,
                                 highlight=h,
                                 format=f)
          else:
            self._generate_blank_image(filename, l, b, highlight=h, format=f)
      else:
        # The file is a text file that needs to be in the logos rpm.
        # These files are found in the share/ folder. If they are not
        # found, they are skipped.
        if sharedfile.exists():
          self.log(4, L3("file '%s' exists in share/" % i))
          self.copy(sharedfile, dir)
        else:
          # required text file not there in shared/ folder, passing for now          
          # FIXME: raise an exception here?
          pass
        
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
  _generate_gradient_image = _generate_image # TODO: Implement this
  
  def _get_image_info(self, logo):
    id = logo.attrib['id']
    location = P(logo.get('location/text()'))
    width = logo.get('width/text()', None)
    height = logo.get('height/text()', None)
    textmaxwidth = logo.get('textmaxwidth/text()', None)
    textvcenter = logo.get('textvcenter/text()', None)
    texthcenter = logo.get('texthcenter/text()', None)
    gradient = logo.get('gradient/text()', 'False') in BOOLEANS_TRUE
    highlight = logo.get('highlight/text()', 'False') in BOOLEANS_TRUE
    format = logo.get('format/text()', 'png')
    
    if width:
      width = int(width)
    if height:
      height = int(height)
    if textmaxwidth:
      textmaxwidth = int(textmaxwidth)
    if textvcenter:
      textvcenter = int(textvcenter)
    if texthcenter:
      texthcenter = int(texthcenter)
    
    return (id, location, width, height, textmaxwidth,
            texthcenter, textvcenter, gradient, highlight, format)


EVENTS = {'RPMS': [LogosRpmEvent]}
