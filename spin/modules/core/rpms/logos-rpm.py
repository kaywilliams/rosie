#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
import gzip

from rendition import shlib
from rendition import pps

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event

from spin.modules.shared import RpmBuildMixin

try:
  import Image
  import ImageDraw
  import ImageFont
except ImportError:
  raise ImportError("missing 'python-imaging' module")

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['LogosRpmEvent']}

class LogosRpmEvent(RpmBuildMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'logos-rpm',
      version = '0.94',
      requires = ['base-info', 'anaconda-version', 'logos-versions'],
      provides = ['custom-rpms-data']
    )

    RpmBuildMixin.__init__(self,
      '%s-logos' % self.product,
      "The %s-logos package contains image files which have been automatically "
      "created by spin and are specific to %s." % (self.product, self.fullname),
      "Icons and pictures related to %s" % self.fullname,
      rpm_license = 'GPLv2',
      default_provides = ['system-logos'],
      default_requires = ['coreutils']
    )

    self.logos_handler = LogosHandler(self, 'logos')

    self.DATA = {
      'config': ['.'],
      'variables': ['pva', 'fullname', 'copyright', 'rpm_release',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'logos-versions\']'],
      'output': [self.build_folder],
      'input':  [],
    }

    self.themes_info = [('infinity', 'infinity.xml')]

  def setup(self):
    obsoletes = [ '%s %s %s' %(n,e,v)
                  for n,e,v in self.cvars.get('logos-versions', [])]
    provides = [ 'system-logos %s %s' % (e,v)
                 for _,e,v in self.cvars.get('logos-versions', [])]
    self._setup_build(obsoletes=obsoletes, provides=provides)

    supplied_logos = self.config.get('logos-path/text()', None)
    if supplied_logos:
      self.DATA['input'].append(supplied_logos)
    self.logos_handler.setup_handler(supplied_logos)

  def _generate(self):
    RpmBuildMixin._generate(self)
    self.logos_handler.copy_distro_images()
    self.logos_handler.copy_common_images()
    self._create_grub_splash_xpm()
    self._generate_custom_theme()
    if self.config.get('write-text/text()', 'True') in BOOLEANS_TRUE:
      self.logos_handler.write_text()

  def _generate_custom_theme(self):
    custom_theme = self.build_folder / 'usr/share/%s/custom.conf' % self.rpm_name
    custom_theme.dirname.mkdirs()
    custom_theme.write_text(
      self.locals.gdm_custom_theme % \
      {'themename': self.config.get('theme/text()', 'Spin')}
    )

  def _get_triggerin(self):
    target1, script1 = self._get_gdm_install_trigger()
    target2, script2 = self._get_background_install_trigger()
    return ['%s:%s' % (target1, script1),
            '%s:%s' % (target2, script2)]

  def _get_triggerun(self):
    target1, script1 = self._get_gdm_uninstall_trigger()
    target2, script2 = self._get_background_uninstall_trigger()
    return ['%s:%s' % (target1, script1),
            '%s:%s' % (target2, script2)]

  def _get_gdm_install_trigger(self):
    gdm_triggerin = self.build_folder / 'gdm-triggerin.sh'
    gdm_triggerin.write_lines([
      'CUSTOM_CONF=%{_sysconfdir}/gdm/custom.conf',
      'THEME_CONF=/usr/share/%s/custom.conf' % self.rpm_name,
      '%{__mv} -f $CUSTOM_CONF $CUSTOM_CONF.rpmsave',
      '%{__cp} $THEME_CONF $CUSTOM_CONF',
    ])
    return 'gdm', gdm_triggerin

  def _get_gdm_uninstall_trigger(self):
    gdm_triggerun = self.build_folder / 'gdm-triggerun.sh'
    gdm_triggerun.write_lines([
      'CUSTOM_CONF=%{_sysconfdir}/gdm/custom.conf',
      'if [ "$2" -eq "0" -o "$1" -eq "0" ]; then',
      '  %{__rm} -f $CUSTOM_CONF.rpmsave',
      'fi',
    ])
    return 'gdm', gdm_triggerun

  def _get_background_install_trigger(self):
    bg_triggerin = self.build_folder / 'bg-triggerin.sh'
    triggerin_lines = [
      'BACKGROUNDS=/usr/share/backgrounds',
      'for default in `ls -1 $BACKGROUNDS/images/default* &> /dev/null || echo $BACKGROUNDS/images/default.jpg`; do',
      '  if [ -e $default ]; then ',
      '    %{__mv} $default $default.rpmsave',
      '  fi',
      '  %{__ln_s} $BACKGROUNDS/spin/2-spin-day.png $default',
      'done',
    ]
    for dir, xml in self.themes_info:
      triggerin_lines.extend([
        'if [ -e $BACKGROUNDS/%s ]; then' % dir,
        '  %%{__mv} $BACKGROUNDS/%s $BACKGROUNDS/%s.rpmsave' % (dir, dir),
        '  %%{__ln_s} $BACKGROUNDS/spin $BACKGROUNDS/%s' % dir,
        '  if [ ! -e $BACKGROUNDS/spin/%s ]; then' % xml,
        '    %%{__ln_s} $BACKGROUNDS/spin/spin.xml $BACKGROUNDS/spin/%s' % xml,
        '  fi',
        'fi'
       ])
    bg_triggerin.write_lines(triggerin_lines)
    return 'desktop-backgrounds-basic', bg_triggerin

  def _get_background_uninstall_trigger(self):
    bg_triggerun = self.build_folder / 'bg-triggerun.sh'
    triggerun_lines = [
      'BACKGROUNDS=/usr/share/backgrounds',
      'if [ "$2" -eq "0" -o "$1" -eq "0" ]; then',
      '  for default in `ls -1 $BACKGROUNDS/images/default* | grep -v "rpmsave"`; do',
      '    %{__rm} -f $default',
      '    %{__mv} -f $default.rpmsave $default',
      '  done',
    ]

    for dir, xml in self.themes_info:
      triggerun_lines.extend([
        '  %%{__rm} -rf $BACKGROUNDS/%s' % dir,
        '  %%{__mv} -f $BACKGROUNDS/%s.rpmsave $BACKGROUNDS/%s' % (dir, dir),
        '  %%{__rm} -f $BACKGROUNDS/spin/%s' % xml,
      ])

    triggerun_lines.append('fi')
    bg_triggerun.write_lines(triggerun_lines)
    return 'desktop-backgrounds-basic', bg_triggerun

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

class LogosHandler(object):
  def __init__(self, ptr, subfolder):
    self.ptr = ptr
    self.subfolder = P(subfolder)

    self.distro_dirs = []
    self.common_dirs = []

  def setup_handler(self, supplied):
    fullname = self.ptr.cvars['base-info']['fullname']
    version  = self.ptr.cvars['base-info']['version']
    try:
      bdfolder = FOLDER_MAPPING[fullname][version]
    except KeyError:
      # See if the version of the input distribution is a bugfix
      found = False
      if FOLDER_MAPPING.has_key(fullname):
        for ver in FOLDER_MAPPING[fullname]:
          if version.startswith(ver):
            found = True
            bdfolder = FOLDER_MAPPING[fullname][ver]
            break
      if not found:
        # if not one of the "officially" supported distros, default
        # to something
        bdfolder = FOLDER_MAPPING['*']['0']

    for dir in self.ptr.SHARE_DIRS:
      self.distro_dirs.append(dir / self.subfolder / bdfolder)
      self.common_dirs.append(dir / self.subfolder / 'common')

    if supplied:
      self.distro_dirs.insert(0, P(supplied))

  def copy_common_images(self):
    for folder in self.common_dirs:
      for src in folder.findpaths(type=pps.constants.TYPE_NOT_DIR):
        dst = self.ptr.build_folder // src.relpathfrom(folder)
        if not dst.exists():
          dst.dirname.mkdirs()
          self.ptr.copy(src, dst.dirname, callback=None)

  def copy_distro_images(self):
    required_xwindow = self.ptr.config.get('include-xwindows-art/text()', 'all').lower()
    xwindow_types = XWINDOW_MAPPING[required_xwindow]
    for file_name in self.ptr.locals.logos_files:
      xwindow_type = self.ptr.locals.logos_files[file_name].get('xwindow_type', 'required')
      if xwindow_type in xwindow_types:
        src = self._find_share_directory(file_name) // file_name
        dst = self.ptr.build_folder // file_name
        dst.dirname.mkdirs()
        self.ptr.copy(src, dst.dirname, callback=None)

  def write_text(self):
    for file_name in self.ptr.locals.logos_files:
      strings = self.ptr.locals.logos_files[file_name].get('strings', None)
      if strings:
        src = self.ptr.build_folder // file_name
        img = Image.open(src)
        for i in strings:
          text_string    = i.get('text', '') % self.ptr.cvars['distro-info']
          halign         = i.get('halign', 'center')
          text_coords    = i.get('text_coords', (img.size[0]/2, img.size[1]/2))
          text_max_width = i.get('text_max_width', img.size[0])
          font_color     = i.get('font_color', 'black')
          font_size      = i.get('font_size', 52)
          font_size_min  = i.get('font_size_min', None)
          font_path      = self._get_font_path(i.get('font',
                                                     'DejaVuLGCSans.ttf'))
          draw = ImageDraw.Draw(img)
          font = ImageFont.truetype(font_path, font_size)
          w, h = draw.textsize(text_string, font)
          if font_size_min:
            while True:
              w, h = draw.textsize(text_string, font)
              if w <= (text_max_width or im.size[0]):
                break
              else:
                font_size -= 1
              if font_size < font_size_min:
                break
              font = ImageFont.truetype(font_path, font_size)

          if halign == 'center':
            draw.text((text_coords[0]-(w/2), text_coords[1]-(h/2)),
                      text_string, font=font, fill=font_color)
          elif halign == 'right':
            draw.text((text_coords[0]-w, text_coords[1]-(h/2)),
                      text_string, font=font, fill=font_color)

        img.save(src, format=img.format)

  def _get_font_path(self, font):
    """
    Given a font file name, returns the full path to the font located in one
    of the share directories
    """
    for path in self.ptr.SHARE_DIRS:
      available_fonts = (path/'fonts').findpaths(glob=font)
      if available_fonts:
        font_path = available_fonts[0]; break
      if not font_path:
        raise RuntimeError("Unable to find font file '%s' in share path(s) "
                           "'%s'" %  font_path, self.ptr.SHARE_DIRS)
    return font_path

  def _find_share_directory(self, file):
    for directory in self.distro_dirs:
      if (directory // file).exists():
        return directory
    raise IOError("Unable to find '%s' in share path(s) '%s'" % \
                  (file[1:], self.distro_dirs))


#----- GLOBAL VARIABLES -----#
XWINDOW_MAPPING = {
  'all':   ['gnome', 'kde', 'required'],
  'gnome': ['gnome', 'required'],
  'kde':   ['kde', 'required'],
  'none':  ['required'],
}

FOLDER_MAPPING = {
  'CentOS': {
    '5': 'c5'
  },
  'Fedora Core': {
    '6': 'f6'
  },
  'Fedora': {
    '7': 'f7',
    '8': 'f8',
    '9': 'f8',
  },
  'Red Hat Enterprise Linux Server': {
    '5': 'r5',
  },
  '*': { # default
    '0': 'r5',
  }
}

