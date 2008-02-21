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
from rendition import pps

from spin.event import Event

from spin.modules.shared import RpmBuildMixin, ImagesGenerator

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['ThemeRpmEvent']}

class ThemeRpmEvent(RpmBuildMixin, Event, ImagesGenerator):
  def __init__(self):
    Event.__init__(self,
      id = 'theme-rpm',
      version = '0.92',
      provides=['custom-rpms-data']
    )

    RpmBuildMixin.__init__(self,
      '%s-theme' % self.product,
      "Set up the theme of the machine",
      "Theme files related to %s" % self.fullname,
      rpm_license = 'GPLv2',
      default_requires = ['coreutils'],
      packagereq_type = 'conditional',
      packagereq_requires = 'gdm'
    )

    ImagesGenerator.__init__(self)

    self.DATA = {
      'variables': ['product', 'pva', 'rpm_release'],
      'config':    ['.'],
      'input' :    [],
      'output':    [self.build_folder],
    }

    self.themes_info = [('infinity', 'infinity.xml')]

  def setup(self):
    self._setup_build()
    self._setup_image_creation('theme')

  def _generate(self):
    RpmBuildMixin._generate(self)
    self._generate_custom_theme()
    self._create_dynamic_images(self.locals.theme_files)
    self._copy_static_images()

  def _generate_custom_theme(self):
    custom_theme = self.build_folder / 'usr/share/%s/custom.conf' % self.rpm_name
    custom_theme.dirname.mkdirs()
    custom_theme.write_text(
      self.locals.gdm_custom_theme % {'themename': self.config.get('theme/text()', 'Spin')}
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
      'for default in `ls -1 $BACKGROUNDS/images/default*`; do',
      '  %{__mv} $default $default.rpmsave',
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
