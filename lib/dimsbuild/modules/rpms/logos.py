from StringIO import StringIO
from os.path  import exists, join, isdir, isfile

import os

from dims.osutils import *
from dims.sync    import sync

import dims.imerge  as imerge
import dims.shlib   as shlib
import dims.xmltree as xmltree

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.misc      import locals_imerge

from lib import ColorMixin, RpmsHandler, RpmsInterface

try:
  import Image
  import ImageDraw
  import ImageFont
  import ImageFilter
except ImportError:
  raise ImportError("missing 'python-imaging' RPM")

EVENTS = [
  {
    'id': 'logos-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'RPMS',
    'requires': ['source-vars', 'anaconda-version'],
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
    self.interface.validate('/distro/rpms/logos-rpm', schemafile='logos-rpm.rng')

class LogosRpmHook(RpmsHandler, ColorMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'logos.logos-rpm'
    
    data =  {
      'config': [
        '/distro/main/fullname/text()',
        '/distro/main/version/text()',
        '/distro/rpms/logos-rpm',
      ],
      'output': [],
    }

    RpmsHandler.__init__(self, interface, data,
                         'logos-rpm', '%s-logos' % interface.product,
                         description='Icons and pictures related to %s' \
                         % interface.config.get('/distro/main/fullname/text()'),
                         long_description='The %s-logos package contains '
                         'image files which have been automatically created '
                         'by dimsbuild and are specific to the %s '
                         'distribution.' \
                         %(interface.product, interface.config.get('/distro/main/fullname/text()')))
    
    ColorMixin.__init__(self)

  def setup(self):
    # set the font to use
    available_fonts = find(join(self.sharepath, 'fonts'), name='*.ttf')
    self.fontfile = available_fonts[0]
    
    expand = (self.product,)*8
    self.imageslocal = locals_imerge(L_LOGOS %expand, self.interface.cvars['anaconda-version'])

    # convert the colors to big endian because the python-imaging
    # library uses big-endian colors.    
    self.setColors(be=True)
    self.bgcolor = int(self.bgcolor, 16)
    self.textcolor = int(self.textcolor, 16)
    self.hlcolor = int(self.hlcolor, 16)
    
    mkdir(join(self.interface.METADATA_DIR, 'images-src/product.img'), parent=True)
  
  def _generate(self):
    self._generate_images()
    self._generate_theme_files()

  def _create_manifest(self): pass # done by get_data_files(), below

  def _get_data_files(self):
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    items = {}
    for logoinfo in self.imageslocal.xpath('//logos/logo', []):
      i,l,_,_,_,_,_,_,_,_ = self._get_image_info(logoinfo)

      file = join(self.output_location, i)
      filename = basename(file)
      filedir = dirname(file)

      installname = basename(l)
      installdir = dirname(l)

      if not exists(file): continue # FIXME: fail if a file is not found?
      
      if filename != installname:
        newfile = join(filedir, installname)
        os.link(file, newfile)
        i = newfile

      if installdir not in items.keys():
        items[installdir] = []

      items[installdir].append(i)

      f.write('%s\n' %(i,))
    f.close()
    
    # convert items to a config-styled string
    rtn = ''
    for item in items.keys():
      dir = ''.join([item, ': '])
      files = ', '.join(items[item])
      rtn = ''.join([rtn, dir, files, '\n\t'])
    return rtn
    
  def _valid(self):
    if self.data.has_key('output'):
      for logoinfo in self.imageslocal.xpath('//logos/logo', []):
        i,_,w,h,_,_,_,_,_,_ = self._get_image_info(logoinfo)
        file = join(self.output_location, i)
        if file.lower().endswith('xpm'):
          # HACK: Assuming that all the .xpm files are valid. It is a fair
          # assumption because all the xpm files are from the share directory
          continue
        if w and h:
          try:
            image = Image.open(file)
          except IOError:
            self.log(4, "file '%s' was not found" %(file,)) # should never happen
            return False
          if image.size != (w,h):
            self.log(4, "file '%s' has invalid dimensions" %(file,))            
            return False
    return True

  def _get_obsoletes(self):
    packages = self.config.xpath('/distro/rpms/logos-rpm/obsoletes/package/text()', [])
    if self.config.get('/distro/rpms/logos-rpm/@use-default-set', 'True') in BOOLEANS_TRUE:
      packages.extend(['fedora-logos', 'centos-logos', 'redhat-logos'])

    if packages:
      return ' '.join(packages)
    return None

  def _get_provides(self):
    packages = self.config.xpath('/distro/rpms/logos-rpm/obsoletes/package/text()', [])
    packages.extend(['redhat-logos = 4.9.3', 'system-logos'])
    if self.config.get('/distro/rpms/logos-rpm/@use-default-set', 'True') in BOOLEANS_TRUE:
      packages.extend(['fedora-logos', 'centos-logos'])
    
    return ' '.join(packages)

  def _get_requires(self):
    return 'redhat-artwork'    

  def _generate_theme_files(self):
    # generate the GdmGreeterTheme.desktop file
    f = open(join(self.output_location, 'gdm', 'themes', self.product, 'GdmGreeterTheme.desktop'), 'w')
    f.write(GDM_GREETER_THEME %(self.product, self.fullname, self.fullname,))
    f.close()
    # generate the %{self.product}.xml file
    f = open(join(self.output_location, 'gdm', 'themes', self.product, '%s.xml' %(self.product,)), 'w')
    f.write(THEME_XML)
    f.close()
  
  def _generate_images(self):
    for logoinfo in self.imageslocal.xpath('//logos/logo', []):
      # (id, _, location, width, height, maxwidth, x, y, gradient, highlight)
      i,_,l,b,m,x,y,g,h,f = self._get_image_info(logoinfo)
      sharedfile = join(self.sharepath, 'logos', i)
      filename = join(self.output_location, i)
      dir = dirname(filename)
      if exists(filename):
        rm(filename, force=True)
      if not isdir(dir):
        mkdir(dir, parent=True)

      if l and b:
        if exists(sharedfile):
          self.log(4, "image '%s' exists in share/" %i)
          sync(sharedfile, dir)
        else:
          self.log(4, "creating '%s'" %(i,))
          if m and x and y:
            self._generate_image(filename, l, b, text='%s %s ' %(self.fullname, self.version),
                                 textcood=(x,y), fontsize=52, maxwidth=m, highlight=h, format=f)
          else:
            self._generate_blank_image(filename, l, b, highlight=h, format=f)
      else:
        # The file is a text file that needs to be in the logos rpm.
        # These files are found in the share/ folder. If they are not
        # found, they are skipped.
        if exists(sharedfile):
          self.log(4, "file '%s' exists in share/" %(i,))
          sync(sharedfile, dir)
        else:
          # required text file not there in shared/ folder, passing for now          
          # FIXME: raise an exception here?
          pass
        
    # HACK: hack to create the splash.xpm file, have to first convert
    # the grub-splash.png to an xpm and then gzip it.
    splash_xpm = join(self.output_location, 'bootloader', 'grub-splash.xpm')
    splash_xgz = '%s.gz' %(splash_xpm,)
    if not exists(splash_xgz):
      splash_png = join(self.output_location, 'bootloader', 'grub-splash.png')
      # TODO: Find a better way to do this conversion.
      shlib.execute('convert %s %s' %(splash_png, splash_xpm,))
      import gzip
      infile = file(splash_xpm, 'rb')
      data = infile.read()
      infile.close()
      outfile = gzip.GzipFile(splash_xgz, 'wb')
      outfile.write(data)
      outfile.close()
  
  def _generate_image(self, filename, width, height, text=None, textcood=(10,10),
                      fontsize=52, maxwidth=100, format='png', font=None,
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
        d.text((textcood[0]-(w/2), textcood[1]-(h/2)), text, font=font, fill=self.textcolor)

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


GDM_GREETER_THEME = '''
# This is not really a .desktop file like the rest, but it\'s useful to treat
# it as such
[GdmGreeterTheme]
Encoding=UTF-8
Greeter=%s.xml
Name=%s Theme
Description=%s Theme
Author=dimsbuild
Screenshot=background.png
'''

L_LOGOS = ''' 
<locals>
  <logos-entries>
    <logos version="0">
      <logo id="bootloader/grub-splash.xpm.gz">
        <location>/boot/grub/splash.xpm.gz</location>
      </logo>
      <logo id="bootloader/grub-splash.png">
        <width>640</width>
        <height>480</height>
        <location>/boot/grub/splash.png</location>
      </logo>
      <logo id="anaconda/syslinux-splash.png">
        <width>640</width>
        <height>300</height>
        <location>/usr/lib/anaconda-runtime/boot/syslinux-splash.png</location>
        <textmaxwidth>600</textmaxwidth>
        <textvcenter>150</textvcenter>
        <texthcenter>320</texthcenter>
      </logo>
      <logo id="anaconda/splashtolss.sh">
        <location>/usr/lib/anaconda-runtime/splashtolss.sh</location>
      </logo>
      <logo id="anaconda/anaconda_header.png">
        <width>800</width>
        <height>89</height>
        <location>/usr/share/anaconda/pixmaps/anaconda_header.png</location>
        <textmaxwidth>750</textmaxwidth>
        <textvcenter>45</textvcenter>
        <texthcenter>400</texthcenter>
      </logo>
      <logo id="anaconda/progress_first-lowres.png">
        <width>350</width>
        <height>224</height>
        <location>/usr/share/anaconda/pixmaps/progress_first-lowres.png</location>
        <textmaxwidth>300</textmaxwidth>
        <texthcenter>175</texthcenter>                
        <textvcenter>112</textvcenter>
        <gradient>True</gradient>
      </logo>
      <logo id="anaconda/progress_first.png">
        <width>507</width>
        <height>325</height>
        <location>/usr/share/anaconda/pixmaps/progress_first.png</location>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>150</textvcenter>
        <texthcenter>250</texthcenter>
        <gradient>True</gradient>
      </logo>
      <logo id="anaconda/splash.png">
        <width>507</width>
        <height>388</height>
        <location>/usr/share/anaconda/pixmaps/splash.png</location>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>194</textvcenter>
        <texthcenter>250</texthcenter>
        <gradient>True</gradient>        
      </logo>
      <logo id="kde-splash/BlueCurve/Theme.rc">
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/Theme.rc</location>
      </logo>
      <logo id="kde-splash/BlueCurve/splash_active_bar.png">
        <width>400</width>
        <height>61</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_active_bar.png</location>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>30</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_bottom.png">
        <width>400</width>
        <height>16</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_bottom.png</location>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>8</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_inactive_bar.png">
        <width>400</width>
        <height>61</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_inactive_bar.png</location>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>30</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_top.png">
        <width>400</width>
        <height>244</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_top.png</location>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>112</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="firstboot/firstboot-header.png">
        <width>800</width>
        <height>58</height>
        <location>/usr/share/firstboot/pixmaps/firstboot-header.png</location>
        <textmaxwidth>750</textmaxwidth>
        <textvcenter>25</textvcenter>
        <texthcenter>400</texthcenter>
        <highlight>True</highlight>
      </logo>
      <logo id="firstboot/firstboot-left.png">
        <width>160</width>
        <height>600</height>
        <location>/usr/share/firstboot/pixmaps/firstboot-left.png</location>
        <highlight>True</highlight>
      </logo>
      <logo id="firstboot/shadowman-round-48.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/firstboot/pixmaps/shadowman-round-48.png</location>
      </logo>
      <logo id="firstboot/splash-small.png">
        <width>550</width>
        <height>200</height>
        <location>/usr/share/firstboot/pixmaps/splash-small.png</location>
        <textmaxwidth>530</textmaxwidth>
        <textvcenter>100</textvcenter>
        <texthcenter>275</texthcenter>
        <highlight>True</highlight>
      </logo>
      <logo id="firstboot/workstation.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/firstboot/pixmaps/workstation.png</location>
      </logo>
      <logo id="gnome-screensaver/lock-dialog-system.glade">
        <location>/usr/share/gnome-screensaver/lock-dialog-system.glade</location>
      </logo>
      <logo id="redhat-pixmaps/rhad.png">
        <width>291</width>
        <height>380</height>
        <location>/usr/share/pixmaps/redhat/rhad.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpm.tif">
        <width>801</width>
        <height>512</height>
        <location>/usr/share/pixmaps/redhat/rpm.tif</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-200.png">
        <width>200</width>
        <height>200</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-200.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-32.png">
        <width>32</width>
        <height>32</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-32.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-32.xpm">
        <width>32</width>
        <height>32</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-32.xpm</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-48.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-48.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-48.xpm">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-48.xpm</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-64.png">
        <width>64</width>
        <height>64</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-64.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-64.xpm">
        <width>64</width>
        <height>64</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-64.xpm</location>
      </logo>
      <logo id="gnome-splash/gnome-splash.png">
        <width>503</width>
        <height>420</height>
        <location>/usr/share/pixmaps/splash/gnome-splash.png</location>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>210</textvcenter>
        <texthcenter>250</texthcenter>
        <gradient>True</gradient>        
      </logo>
      <logo id="rhgb/main-logo.png">
        <width>320</width>
        <height>396</height>
        <location>/usr/share/rhgb/main-logo.png</location>
        <textmaxwidth>320</textmaxwidth>
        <textvcenter>190</textvcenter>
        <texthcenter>160</texthcenter>        
      </logo>
      <logo id="rhgb/system-logo.png">
        <width>183</width>
        <height>45</height>
        <location>/usr/share/rhgb/system-logo.png</location>
        <textmaxwidth>150</textmaxwidth>
        <textvcenter>22</textvcenter>
        <texthcenter>90</texthcenter>        
      </logo>
      <logo id="gdm/themes/%s/background.png">
        <width>635</width>
        <height>480</height>
        <location>/usr/share/gdm/themes/%s/background.png</location>
        <gradient>True</gradient>        
      </logo>
      <logo id="gdm/themes/%s/GdmGreeterTheme.desktop">
        <location>/usr/share/gdm/themes/%s/GdmGreeterTheme.desktop</location>
      </logo>
      <logo id="gdm/themes/%s/%s.xml">
        <location>/usr/share/gdm/themes/%s/%s.xml</location>
      </logo>
    </logos>
    <logos version="11.2.0.66-1">
      <action type="insert" path=".">
        <logo id="anaconda/syslinux-vesa-splash.jpg">
          <location>/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg</location>
          <width>640</width>
          <height>480</height>
          <format>jpeg</format>
        </logo>
      </action>
    </logos>
  </logos-entries>
</locals>
'''

THEME_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE greeter SYSTEM "greeter.dtd">
<greeter>
  <item type="pixmap">
    <normal file="background.png"/>
    <pos x="0" y="0" width="100%" height="-75"/>
  </item>
  
  <item type="rect">
    <normal color="#000000"/>
    <pos x="0" y="-75" width="100%" height="75"/>
    <fixed>
      <item type="rect">
        <normal color="#ffffff"/>
        <pos x="0" y="4" width="100%" height="100%"/>
        <box orientation="horizontal" spacing="10" xpadding="10" ypadding="10">
          <item type="button" id="options_button">
            <pos width="100" height="50" />
            <stock type="options"/>
          </item>
        </box>
      </item>
    </fixed>
  </item>

  <item type="label" id="clock">
    <normal color="#000000" font="Sans 12"/>
    <pos x="-160" y="-37" anchor="e"/>
    <text>%c</text>
  </item>

  <item type="rect" id="caps-lock-warning">
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="75%" width="box" height="box"/>
    <box orientation="vertical" min-width="400" xpadding="10" ypadding="5" spacing="0">
      <item type="label">
        <normal color="#000000" font="Sans 12"/>
        <pos x="50%" anchor="n"/>
	<!-- Stock label for: You've got capslock on! -->
	<stock type="caps-lock-warning"/>
      </item>
    </box>
  </item>

  <item type="rect">
    <show type="timed"/>
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="25%" width="box" height="box"/>
    <box orientation="vertical" min-width="400" xpadding="10" ypadding="5" spacing="0">
      <item type="label" id="timed-label">
        <normal color="#000000" font="Sans 12"/>
        <pos x="50%" anchor="n"/>
	<!-- Stock label for: User %s will login in %d seconds -->
	<stock type="timed-label"/>
      </item>
    </box>
  </item>

  <item type="rect">
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="50%" width="box" height="box"/>
    <box orientation="vertical" min-width="340" xpadding="30" ypadding="30" spacing="10">
      <item type="label">
        <pos anchor="n" x="50%"/>
        <normal color="#000000" font="Sans 14"/>
	<!-- Stock label for: Welcome to %h -->
	<stock type="welcome-label"/>
      </item>
      <item type="label" id="pam-prompt">
        <pos anchor="nw" x="10%"/>
        <normal color="#000000" font="Sans 12"/>
	<!-- Stock label for: Username: -->
	<stock type="username-label"/>
      </item>
      <item type="rect">
	<normal color="#000000"/>
        <pos anchor="n" x="50%" height="24" width="80%"/>
	<fixed>
	  <item type="entry" id="user-pw-entry">
            <normal color="#000000" font="Sans 12"/>
            <pos anchor="nw" x="1" y="1" height="-2" width="-2"/>
	  </item>
	</fixed>
      </item>
      <item type="button" id="ok_button">
        <pos anchor="n" x="50%" height="32" width="50%"/>
        <stock type="ok"/>
      </item>
      <item type="button" id="cancel_button">
        <pos anchor="n" x="50%" height="32" width="50%"/>
        <stock type="startagain"/>
      </item>
      <item type="label" id="pam-message">
        <pos anchor="n" x="50%"/>
        <normal color="#000000" font="Sans 12"/>
	<text></text>
      </item>
    </box>
    <fixed>
      <item type="label" id="pam-error">
        <pos anchor="n" x="50%" y="110%"/>
        <normal color="#000000" font="Sans 12"/>
        <text></text>
      </item>
    </fixed>
  </item>
</greeter>
"""
