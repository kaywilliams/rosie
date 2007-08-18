from os.path  import exists, join, isdir, isfile

import os

from dims import osutils
from dims import shlib
from dims import sync

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.misc      import locals_imerge

from lib       import ColorMixin, RpmBuildHook, RpmsInterface
from rpmlocals import L_LOGOS, GDM_GREETER_THEME, THEME_XML

try:
  import Image
  import ImageDraw
  import ImageFont
  import ImageFilter
except ImportError:
  raise ImportError("missing 'python-imaging' RPM")

EVENTS = [
  {
    'id':        'logos-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent':    'RPMS',
    'requires':  ['source-vars', 'anaconda-version'],
  },
]

HOOK_MAPPING = {
  'LogosRpmHook': 'logos-rpm',
  'ValidateHook': 'validate',
}

API_VERSION = 4.1


#---------- HOOKS -------------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'logos.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/rpms/logos-rpm',
                            schemafile='logos-rpm.rng')

class LogosRpmHook(RpmBuildHook, ColorMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'logos.logos-rpm'
    
    data =  {
      'config': ['/distro/rpms/logos-rpm'],
      'variables': ['fullname',
                    'product'],
      'output': [],
    }

    packages = interface.config.xpath(
      '/distro/rpms/logos-rpm/obsoletes/package/text()', []
    )
    if interface.config.get('/distro/rpms/logos-rpm/@use-default-set', 'True') \
           in BOOLEANS_TRUE:
      packages.extend(['fedora-logos', 'centos-logos', 'redhat-logos'])
    if packages:
      obsoletes = ' '.join(packages)
    else:
      obsoletes = None

    provides = 'redhat-logos = 4.9.3 system-logos'
    if obsoletes:
      provides = provides + ' ' + obsoletes    
    
    RpmBuildHook.__init__(self, interface, data, 'logos-rpm',
                           '%s-logos' % interface.product,
                           summary='Icons and pictures related to '
                           '%s' % interface.fullname,
                           description='The %s-logos package '
                           'contains image files which have been '
                           'automatically created by dimsbuild and are '
                           'specific to the %s distribution.' \
                           % (interface.product, interface.fullname),
                           provides=provides,
                           requires='redhat-artwork',
                           obsoletes=obsoletes)
    
    ColorMixin.__init__(self)

  def setup(self):
    RpmBuildHook.setup(self)
    
    # set the font to use
    available_fonts = osutils.find(join(self.interface.sharepath, 'fonts'),
                                   name='*.ttf')
    try:
      self.fontfile = available_fonts[0]
    except IndexError:
      raise RuntimeError("Unable to find any font files in share path '%s'" % self.interface.sharepath)
    
    expand = (self.interface.product,)*8
    self.imageslocal = locals_imerge(L_LOGOS %expand,
                                     self.interface.cvars['anaconda-version'])

    # convert the colors to big endian because the python-imaging
    # library uses big-endian colors.    
    self.setColors(be=True)
    self.bgcolor = int(self.bgcolor, 16)
    self.textcolor = int(self.textcolor, 16)
    self.hlcolor = int(self.hlcolor, 16)
  
  def generate(self):
    self._generate_images()
    self._generate_theme_files()

  def _get_data_files(self):
    items = RpmBuildHook._get_data_files(self)
    for logoinfo in self.imageslocal.xpath('//logos/logo', []):
      i,l,_,_,_,_,_,_,_,_ = self._get_image_info(logoinfo)

      file = join(self.build_folder, i)
      filename = osutils.basename(file)
      filedir = osutils.dirname(file)

      installname = osutils.basename(l)
      installdir = osutils.dirname(l)

      if not exists(file): continue # FIXME: fail if a file is not found?
      
      if filename != installname:
        newfile = join(filedir, installname)
        os.link(file, newfile)
        i = newfile

      if installdir not in items.keys():
        items[installdir] = []

      items[installdir].append(i)
    return items
    
  def output_valid(self):
    if self.DATA.has_key('output'):
      for logoinfo in self.imageslocal.xpath('//logos/logo', []):
        i,_,w,h,_,_,_,_,_,_ = self._get_image_info(logoinfo)
        file = join(self.build_folder, i)
        if file.lower().endswith('xpm'):
          # HACK: Assuming that all the .xpm files are valid. It is a fair
          # assumption because all the xpm files are from the shared directory
          continue
        if w and h:
          try:
            image = Image.open(file)
          except IOError:
            # should never happen
            self.interface.log(4, "file '%s' was not found" % file) 
            return False
          if image.size != (w,h):
            self.interface.log(4, "file '%s' has invalid dimensions" % file)   
            return False
    return True

  def _generate_theme_files(self):
    # generate the GdmGreeterTheme.desktop file
    f = open(join(self.build_folder, 'gdm', 'themes',
                  self.interface.product, 'GdmGreeterTheme.desktop'), 'w')
    f.write(GDM_GREETER_THEME %(self.interface.product, self.interface.fullname,
                                self.interface.fullname,))
    f.close()
    # generate the %{self.interface.product}.xml file
    f = open(join(self.build_folder, 'gdm', 'themes',
                  self.interface.product, '%s.xml' % self.interface.product),
             'w')
    f.write(THEME_XML)
    f.close()
  
  def _generate_images(self):
    for logoinfo in self.imageslocal.xpath('//logos/logo', []):
      # (id, _, location, width, height, maxwidth, x, y, gradient, highlight)
      i,_,l,b,m,x,y,g,h,f = self._get_image_info(logoinfo)
      sharedfile = join(self.interface.sharepath, 'logos', i)
      filename = join(self.build_folder, i)
      dir = osutils.dirname(filename)
      if exists(filename):
        osutils.rm(filename, force=True)
      if not isdir(dir):
        osutils.mkdir(dir, parent=True)

      if l and b:
        if exists(sharedfile):
          self.interface.log(4, "image '%s' exists in share/" %i)
          sync.sync(sharedfile, dir)
        else:
          self.interface.log(4, "creating '%s'" %i)
          if m and x and y:
            self._generate_image(filename, l, b,
                                 text='%s %s ' %(self.interface.fullname,
                                                 self.interface.version),
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
        if exists(sharedfile):
          self.interface.log(4, "file '%s' exists in share/" % i)
          sync.sync(sharedfile, dir)
        else:
          # required text file not there in shared/ folder, passing for now          
          # FIXME: raise an exception here?
          pass
        
    # HACK: hack to create the splash.xpm file, have to first convert
    # the grub-splash.png to an xpm and then gzip it.
    splash_xpm = join(self.build_folder, 'bootloader', 'grub-splash.xpm')
    splash_xgz = '%s.gz' % splash_xpm
    if not exists(splash_xgz):
      splash_png = join(self.build_folder, 'bootloader', 'grub-splash.png')

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
    location = logo.get('location/text()')    
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

