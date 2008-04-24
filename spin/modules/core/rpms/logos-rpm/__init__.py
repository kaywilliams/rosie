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

from constants import *
from handlers  import *

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['LogosRpmEvent']}

class LogosRpmEvent(RpmBuildMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'logos-rpm',
      version = '0.95',
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

    self.handlers = []

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
    self._setup_handlers()

  def _generate(self):
    RpmBuildMixin._generate(self)
    for handler in self.handlers:
      handler.generate()
    self._create_grub_splash_xpm()
    self._generate_custom_theme()

  def _setup_handlers(self):
    info = self._get_distro_info()

    # setup user-specified handler
    supplied_logos = self.config.get('logos-path/text()', None)
    if supplied_logos:
      self.DATA['input'].append(supplied_logos)
      self.handlers.append(UserSpecifiedHandler(self, [supplied_logos]))

    distro_paths, common_paths, fallback_paths = self._get_handler_paths(info['folder'])

    write_text = self.config.get('write-text/text()', 'True') in BOOLEANS_TRUE
    if distro_paths:
      self.handlers.append(DistroSpecificHandler(self, distro_paths, write_text))
    if common_paths:
      self.handlers.append(CommonFilesHandler(self, common_paths))
    if fallback_paths:
      self.handlers.append(FallbackHandler(self, fallback_paths,
                                           info['start_color'],
                                           info['end_color'],
                                           write_text))

  def _generate_custom_theme(self):
    custom_theme = self.build_folder / 'usr/share/%s/custom.conf' % self.rpm_name
    custom_theme.dirname.mkdirs()
    custom_theme.write_text(
      self.locals.L_GDM_CUSTOM_THEME % \
      {'themename': self.config.get('theme/text()', 'Spin')}
    )

  def _get_post_install_script(self):
    post_install = self.build_folder / 'post-install.sh'
    post_install.write_lines([
      'SPIN_BACKGROUNDS="1-spin-sunrise.png 2-spin-day.png 3-spin-sunset.png 4-spin-night.png"',
      'DEFAULT=/usr/share/backgrounds/spin/default.jpg',
      'for file in $SPIN_BACKGROUNDS; do',
      '  %{__ln_s} $DEFAULT /usr/share/backgrounds/spin/$file',
      'done'
    ])
    return post_install

  def _get_post_uninstall_script(self):
    post_uninstall = self.build_folder / 'post-uninstall.sh'
    post_uninstall.write_lines([
      'SPIN_BACKGROUNDS="1-spin-sunrise.png 2-spin-day.png 3-spin-sunset.png 4-spin-night.png"',
      'for file in $SPIN_BACKGROUNDS; do',
      '  %{__rm} -f /usr/share/backgrounds/spin/$file',
      'done'
    ])
    return post_uninstall

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
      'DEFAULTS="default-5_4.jpg default-dual.jpg default-dual-wide.jpg default.jpg default-wide.jpg"',
      'for default in $DEFAULTS; do',
      '  file=$BACKGROUNDS/images/$default',
      '  if [ -e $file ]; then',
      '    %{__mv} $file $file.rpmsave',
      '    %{__ln_s} $BACKGROUNDS/spin/$default $file',
      '  fi',
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

  def _get_distro_info(self):
    fullname = self.cvars['base-info']['fullname']
    version  = self.cvars['base-info']['version']
    try:
      info = DISTRO_INFO[fullname][version]
    except KeyError:
      # See if the version of the input distribution is a bugfix
      found = False
      if DISTRO_INFO.has_key(fullname):
        for ver in DISTRO_INFO[fullname]:
          if version.startswith(ver):
            found = True
            info = DISTRO_INFO[fullname][ver]
            break
      if not found:
        # if not one of the "officially" supported distros, default
        # to something
        info = DISTRO_INFO['*']['0']
    return info

  def _get_handler_paths(self, distro_folder):
    # setup distro-specific, common files, and fallback handlers
    required_xwindow = self.config.get('include-xwindows-art/text()', 'all').lower()
    xwindow_types = XWINDOW_MAPPING[required_xwindow]

    distro_paths = []
    common_paths = []
    fallback_paths = []
    for shared_dir in [ x / 'logos' for x in self.SHARE_DIRS ]:
      distro = shared_dir / 'distros' / distro_folder
      common = shared_dir / 'common'
      fallback = shared_dir / 'fallback'
      for paths, folder in [(distro_paths, distro),
                            (common_paths, common),
                            (fallback_paths, fallback)]:
        required = folder / 'required'
        gnome = folder / 'gnome'
        kde = folder / 'kde'
        if required.exists():
          paths.append(required)
        if 'gnome' in xwindow_types and gnome.exists():
          paths.append(gnome)
        if 'kde' in xwindow_types and kde.exists():
          paths.append(kde)
    return distro_paths, common_paths, fallback_paths

