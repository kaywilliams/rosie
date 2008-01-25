from rendition import pps

from spin.event import Event

from spin.modules.shared import RpmBuildMixin, ImagesGenerator

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['ThemeRpmEvent']}

class ThemeRpmEvent(Event, RpmBuildMixin, ImagesGenerator):
  def __init__(self):
    self.themename = self.config.get('theme/text()', 'Spin')

    Event.__init__(self,
      id = 'theme-rpm',
      version = '0.91',
      provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info']
    )

    RpmBuildMixin.__init__(self,
      '%s-theme' % self.product,
      "Set up the theme of the machine",
      "Theme files related to %s" % self.fullname,
      rpm_license = 'GPLv2',
      default_requires = ['coreutils']
    )

    ImagesGenerator.__init__(self)

    self.DATA = {
      'variables': ['product', 'pva', 'rpm_release'],
      'config':    ['.'],
      'input' :    [],
      'output':    [self.build_folder],
    }

    self.custom_theme = self.build_folder / 'usr/share/%s/custom.conf' % self.rpm_name

    self.themes_info = [('infinity', 'infinity.xml')]
    self.backgrounds = ['default.jpg', 'default.png',
                        'default-5_4.png', 'default-wide.png']

  def setup(self):
    self._setup_build()

  def run(self):
    self.io.clean_eventcache(all=True)
    self._build_rpm()
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self._check_rpms()
    self.cvars.setdefault('custom-rpms-info', []).append(
      (self.rpm_name, 'conditional', 'gdm', self.rpm_obsoletes, None)
    )

  def _generate(self):
    RpmBuildMixin._generate(self)
    self._generate_custom_theme()
    self.create_images(self.locals.theme_files)
    self.copy_images('theme')

  def _generate_custom_theme(self):
    self.custom_theme.dirname.mkdirs()
    self.custom_theme.write_text(
      self.locals.gdm_custom_theme % {'themename': self.themename}
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
    gdm_install_trigger = self.build_folder / 'gdm-install-trigger.sh'
    custom_conf  = '/%s' % self.custom_theme.relpathfrom(self.build_folder)
    gdm_install_trigger.write_lines([
      'THEME_CUSTOM_CONF=%s' % custom_conf,
      'CUSTOM_CONF=%{_sysconfdir}/gdm/custom.conf',
      '%{__mv} $CUSTOM_CONF $CUSTOM_CONF.rpmsave',
      '%{__cp} $THEME_CUSTOM_CONF $CUSTOM_CONF'
    ])
    return 'gdm', gdm_install_trigger

  def _get_background_install_trigger(self):
    bg_install_trigger = self.build_folder / 'bg-install-trigger.sh'
    lines = ['BACKGROUNDS=%{_datadir}/backgrounds']

    for file in self.backgrounds:
      lines.extend([
        'if [ -e $BACKGROUNDS/images/%s ]; then' % file,
        '  %%{__mv} $BACKGROUNDS/images/%s $BACKGROUNDS/images/%s.rpmsave' % (file, file),
        '  %%{__cp} $BACKGROUNDS/spin/2-spin-day.png $BACKGROUNDS/images/%s' % file,
        'fi'
      ])

    for dir, xml in self.themes_info:
      lines.extend([
        'if [ -d $BACKGROUNDS/%s ]; then' % dir,
        '  if [ -d $BACKGROUNDS/%s.rpmsave ]; then' % dir,
        '    %%{__rm} -rf $BACKGROUNDS/%s.rpmsave' % dir,
        '  fi',
        '  %%{__mv} $BACKGROUNDS/%s $BACKGROUNDS/%s.rpmsave' % (dir, dir),
        '  %%{__ln_s} $BACKGROUNDS/spin $BACKGROUND/%s' % dir,
        '  if [ ! -e $BACKGROUNDS/spin/%s ]; then' % xml,
        '    %%{__ln_s} $BACKGROUNDS/spin/spin.xml $BACKGROUNDS/spin/%s' % xml,
        '  fi',
        'fi',
      ])
    bg_install_trigger.write_lines(lines)
    return 'desktop-backgrounds-basic', bg_install_trigger

  def _get_gdm_uninstall_trigger(self):
    gdm_uninstall_trigger = self.build_folder / 'gdm-uninstall-trigger.sh'
    gdm_uninstall_trigger.write_lines([
      'if [ "$1" -eq "0" -o "$2" -eq "0" ]; then',
      '  rm -f %{_sysconfdir}/gdm/custom.conf.rpmsave',
      'fi'
    ])
    return 'gdm', gdm_uninstall_trigger

  def _get_background_uninstall_trigger(self):
    bg_uninstall_trigger = self.build_folder / 'bg-uninstall-trigger.sh'
    lines = [
      'if [ "$1" -eq "0" -o "$2" -eq "0" ]; then',
      '  BACKGROUNDS=%{_datadir}/backgrounds']
    for file in self.backgrounds:
      lines.extend([
        '  if [ -e $BACKGROUNDS/images/%s.rpmsave ]; then' % file,
        '    %%{__rm} $BACKGROUNDS/images/%s.rpmsave' % file,
        '  fi',
      ])

    for dir, xml in self.themes_info:
      lines.extend([
        '  if [ -d $BACKGROUNDS/%s.rpmsave ]; then' % dir,
        '    %%{__rm} -rf $BACKGROUNDS/%s.rpmsave' % dir,
        '    %%{__rm} -f $BACKGROUNDS/spin/%s' % xml,
        '  fi'
      ])
    lines.append('fi')

    bg_uninstall_trigger.write_lines(lines)
    return 'desktop-backgrounds-basic', bg_uninstall_trigger
