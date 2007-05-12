import os

import dims.shlib as shlib
import dims.xmltree as xmltree
import dims.imerge as imerge

from StringIO import StringIO
from dims.osutils import basename, dirname, mkdir
from dims.sync import sync
from event import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from lib import RpmHandler, RpmsInterface, addHandler, getHandler
from os.path import exists, join, isdir, isfile
from output import MorphStructMixin, tree

try:
  import Image
  import ImageDraw
  import ImageFilter
  import ImageFont
except ImportError:
  raise ImportError, "missing 'python-imaging' RPM"

EVENTS = [
  {
    'id': 'logos',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['logos-rpm'],
    'parent': 'RPMS',
  },
]

L_LOGOS = """
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
        <textmaxwidth>600</textmaxwidth>
        <textvcenter>240</textvcenter>
        <texthcenter>320</texthcenter>
      </logo>
      <logo id="anaconda/syslinux-splash.png">
        <width>640</width>
        <height>300</height>
        <location>/usr/lib/anaconda-runtime/boot/syslinux-splash.png</location>
        <textmaxwidth>300</textmaxwidth>
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
        <textvcenter>112</textvcenter>
        <texthcenter>175</texthcenter>        
      </logo>
      <logo id="anaconda/progress_first.png">
        <width>507</width>
        <height>325</height>
        <location>/usr/share/anaconda/pixmaps/progress_first.png</location>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>150</textvcenter>
        <texthcenter>250</texthcenter>        
      </logo>
      <logo id="anaconda/splash.png">
        <width>507</width>
        <height>388</height>
        <location>/usr/share/anaconda/pixmaps/splash.png</location>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>194</textvcenter>
        <texthcenter>250</texthcenter>        
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
      </logo>
      <logo id="firstboot/firstboot-left.png">
        <width>160</width>
        <height>600</height>
        <location>/usr/share/firstboot/pixmaps/firstboot-left.png</location>
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
        <textmaxwidth>500</textmaxwidth>
        <textvcenter>100</textvcenter>
        <texthcenter>250</texthcenter>        
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
      </logo>
      <logo id="rhgb/main-logo.png">
        <width>320</width>
        <height>396</height>
        <location>/usr/share/rhgb/main-logo.png</location>
        <textmaxwidth>250</textmaxwidth>
        <textvcenter>198</textvcenter>
        <texthcenter>160</texthcenter>        
      </logo>
      <logo id="rhgb/system-logo.png">
        <width>183</width>
        <height>45</height>
        <location>/usr/share/rhgb/system-logo.png</location>
        <textmaxwidth>120</textmaxwidth>
        <textvcenter>22</textvcenter>
        <texthcenter>90</texthcenter>        
      </logo>
      <logo id="COPYING">
        <location>/usr/share/NVR/COPYING</location>
      </logo>
    </logos>
  </logos-entries>
</locals>
"""

#-------------- METADATA STRUCTS ---------#
LOGOS_MD_STRUCT = {
    'config': [
      '/distro/main/fullname/text()',
      '/distro/main/version/text()',
      '//logos-rpm',
    ],
    'output': [
      'builddata/logos-rpm/',
    ]
  }


def locals_imerge(string, ver='0'):
  tree = xmltree.read(StringIO(string))
  locals = xmltree.Element('locals')
  for child in tree.getroot().getchildren():
    locals.append(imerge.incremental_merge(child, ver))
  return locals

#------ HOOK FUNCTIONS ------#
def prelogos_hook(interface):
  handler = LogosRpmHandler(interface, LOGOS_MD_STRUCT)
  addHandler(handler, 'logos')
  interface.disableEvent('logos')
  if interface.pre(handler) or (interface.eventForceStatus('logos') or False):
    interface.enableEvent('logos')
  mkdir(join(interface.getMetadata(), 'images-src/product.img'), parent=True)
        
def logos_hook(interface):
  interface.log(0, "processing logos")
  handler = getHandler('logos')
  interface.modify(handler)

def postlogos_hook(interface):
  handler = getHandler('logos')
  if handler.create:
    # add rpms to the included-packages control var, so that
    # they are added to the comps.xml
    interface.append_cvar('included-packages', [handler.rpmname])
    
    # add rpms to the excluded-packages control var, so that
    # they are removed from the comps.xml
    interface.append_cvar('excluded-packages', handler.obsoletes.split())

#---------- HANDLERS -------------#
class LogosRpmHandler(RpmHandler, MorphStructMixin):
  def __init__(self, interface, data):      
    MorphStructMixin.__init__(self, interface.config)        

    RpmHandler.__init__(self, interface, data,
                        elementname='logos-rpm',
                        rpmname='%s-logos' %(interface.product,),
                        provides_test='redhat-logos',
                        provides='system-logos, redhat-logos = 4.9.3',
                        obsoletes = 'fedora-logos centos-logos redhat-logos',
                        description='Icons and pictures related to %s' \
                          %(interface.config.get('//main/fullname/text()'),),
                        long_description='The %s-logos package contains '
                          'image files which have been automatically created '
                          'by dimsbuild and are specific to the %s '
                          'distribution.' \
                          %(interface.product, interface.config.get('//main/fullname/text()'),))

    if self.data.has_key('input'):
      self.expandInput(self.data)
    if self.data.has_key('output'):
      self.expandOutput(self.data, dirname(self.metadata)) # the 'output' element has entries
                                                           # relative to dirname(self.metadata)

    self.share_path = self.interface._base.sharepath
    self.locals = locals_imerge(L_LOGOS)
    self.build_controlset()
    
  def build_controlset(self):
    def get_value(logo, name, optional=False):
      try:
        return logo.iget(name).text
      except AttributeError:
        if optional:
          return None
        else:
          raise
    self.controlset = {}
    for logo in self.locals.get('//logo'):
      id = logo.attrib['id']
      install_path = get_value(logo, 'location')      
      file_name = basename(id)
      dir_name = dirname(id)
      self.controlset[id] = {
        'install_path': install_path,
        'file_name': file_name,
        'dir_name': dir_name,
        }      
      for optional_item in ['width', 'height', 'textmaxwidth', 'textvcenter', 'texthcenter']:
        value = get_value(logo, optional_item, optional=True)
        if value:
          self.controlset[id][optional_item] = int(value)
        else:
          self.controlset[id][optional_item] = None

  def testOutputValid(self):
    if self.create:
      if self.data.has_key('output'):
        for id in self.controlset.keys():
          file = join(self.output_location, id)
          # TODO: Fail if a file in the control list is not found
          if file[-3:].lower() == 'xpm':
            # assume that all xpm files are fine, because the python-imaging
            # chokes on them. The xpm files used in the logos RPM are static
            # ones, so it is "fine" to make this assumption. 
            continue               
          if not self._verify_file(file, self.controlset[id]):
            self.log(4, "file '%s' has invalid dimensions" %(file,))
            return False
    return True
            
  def addOutput(self):
    if self.create:
      # get the font file, either from the config file or the dimsbuild's shared folder
      ttf_file = self.config.get('//%s/font-file/text()' %(self.elementname,), None)
      if not ttf_file:
        fallback_fonts = filter(lambda x: x.find('svn') == -1,
                                tree(join(self.share_path, 'fonts'), prefix=True,
                                     type='f|l'))
        ttf_file = fallback_fonts[0]
      
      for id in self.controlset.keys():
        shared_file = join(self.share_path, 'logos', id)
        file_name = join(self.output_location, id)
        dir = dirname(file_name)
        if exists(file_name):
          continue
        if not isdir(dir):
          mkdir(dir, parent=True)
        if self.controlset[id]['width'] and self.controlset[id]['height']:
          if exists(shared_file):
            self.log(4, "image '%s' exists in the share/" %(id,))
            sync(shared_file, dir)
          else:
            width = self.controlset[id]['width']
            height = self.controlset[id]['height']
            textmaxwidth = self.controlset[id]['textmaxwidth']
            text_xcood = self.controlset[id]['texthcenter']
            text_ycood = self.controlset[id]['textvcenter']
            self.log(4, "creating '%s'" %(id,))
            if textmaxwidth and text_xcood and text_ycood:
              self._generate_image(file_name, width, height,
                                   font_file=ttf_file,
                                   font_size=50,
                                   text_width=textmaxwidth,
                                   text='%s %s'%(self.fullname,
                                                 self.version),
                                   text_cood=(text_xcood,text_ycood),
                                   format='png')
            else:
              self._generate_image(file_name, width, height)              
        else:
          # The file is a text file that needs to be in the logos rpm.
          # These files are found in the share/ folder. If they are not
          # found, they are skipped; this needs to change eventually.
          if exists(shared_file):
            self.log(4, "file '%s' exists in share/" %(id,))
            sync(shared_file, dir)
          else: # required text file not there in shared/ folder, passing for now
            pass
      # hack to create the splash.xpm file, have to first convert
      # the grub-splash.png to an xpm and then gzip it.
      splash_xpm = join(self.output_location, 'bootloader', 'grub-splash.xpm')
      splash_xgz = '%s.gz' %(splash_xpm,)
      splash_png = join(self.output_location, 'bootloader', 'grub-splash.png')
      if not exists(splash_xgz):
        shlib.execute('convert %s %s' %(splash_png, splash_xpm,))
        import gzip
        infile = file(splash_xpm, 'rb')
        data = infile.read()
        infile.close()
        outfile = gzip.GzipFile(splash_xgz, 'wb')
        outfile.write(data)
        outfile.close()
      RpmHandler.addOutput(self)
        
  def _get_data_files(self):
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    items = {}
    for id in self.controlset.keys():      
      file = join(self.output_location, id)
      file_name = basename(file)
      file_dir = dirname(file)
      
      install_file = self.controlset[id]['install_path']
      install_filename = basename(install_file)            
      install_dir = dirname(install_file)
      
      if exists(file):
        if file_name != install_filename:
          new_file = join(file_dir, install_filename)
          os.link(file, new_file)
          id = join(file_dir, install_filename)
        if install_dir in items.keys():
          items[install_dir].append(id)
        else:
          items[install_dir] = [id]
        f.write('%s\n' %(id,))
    f.close()
    # convert items to a config-styled string
    rtn = ''
    for item in items.keys():
      dir = ''.join([item, ': '])
      files = ', '.join(items[item])
      rtn = ''.join([rtn, dir, files, '\n\t'])
    return rtn
        
  def _generate_image(self, file_name, width, height, font_size=0, font_file=None, 
                      text_width=100, text=None, text_cood=(10,10), format='png'):
    """ 
    Generate an image that is added to the logos RPM and the product.img.

    @param file_name  : the name of the file to be generated
    @param width      : the width of the image
    @param height     : the height of the image
    @param font_size  : the 'starting' font size of the text on the image
    @param text       : the text to be added to the image
    @param text_cood  : coordinates of the center of the text block
    @param text_width : maximum length of the text block
    @param format     : the format of the image: png, jpeg etc.
    """
    def _get_font(width, height, xcood, ycood, textmaxwidth, text, font_file, font_size):
      startX = xcood - textmaxwidth/2
      font = ImageFont.truetype(font_file, font_size)
      (text_width, text_height) = font.getsize(text)
      startY = ycood - text_height/2
      while (text_width > textmaxwidth) or \
                ((startX+text_width) > width) or \
                ((startY+text_height) > height):
        if text_height <= 10: # have to decide on a "good" minimum font size
          break               # 10 pixels good enough?
        font_size = font_size - 2
        font = ImageFont.truetype(font_file, font_size)
        (text_width, text_height) = font.getsize(text)
        startY = ycood - text_height/2
      return font

    def get_color(xquery, fallback):
      # the python-imaging library accepts big-endian colors, this
      # function, swaps the first and the third byte in the user-specified
      # color, and returns it. HACK :(.
      color = self.config.get(xquery, fallback)
      if color.startswith('0x'):
        color = color[2:]
      color = '%s%s' % ((6-len(color))*'0', color) # prepend zeroes to color
      return int('0x%s%s%s' % (color[4:], color[2:4], color[:2]), 16)
      
    im = Image.new('RGB', (width, height),
                   get_color('//%s/background-color/text()' %(self.elementname,), '0x285191'))
    # add text to the image, if specified
    if text:
      font = _get_font(width, height,
                       text_cood[0],
                       text_cood[1],
                       text_width,
                       text, font_file, font_size)
      dim = font.getsize(text)
      d = ImageDraw.Draw(im)
      d.text((text_cood[0]-dim[0]/2, text_cood[1]-dim[1]/2), text, font=font,
             fill=get_color('//%s/text-color/text()' %(self.elementname,), '0xffffff'))
    # save the image to a file
    im.save(file_name, format=format)        

  def _get_path_id(self, filename):
    for item in self.controlset.keys():
      if self.controlset[item]['file_name'] == filename:
        return item
    return None        

  def _verify_file(self, input, control):
    width = control['width']
    height = control['height']
    if width and height:
      control_size = (width, height)
      try:
        image = Image.open(input)
      except IOError:
        return False
      input_size = image.size
      if input_size != control_size:
        return False
    return True
