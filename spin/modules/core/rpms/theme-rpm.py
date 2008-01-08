from rendition import pps

from spin.event import Event

from spin.modules.shared import RpmBuildMixin, ImagesCreator

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['ThemeRpmEvent']}

class ThemeRpmEvent(Event, RpmBuildMixin, ImagesCreator):
  def __init__(self):
    self.themename = self.config.get('theme/text()', 'Spin')

    Event.__init__(self,
      id = 'theme-rpm',
      version = 3,
      provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info']
    )

    RpmBuildMixin.__init__(self,
      '%s-theme' % self.product,
      "Set up the theme of the machine",
      "Theme files related to %s" % self.fullname,
      rpm_license = 'GPLv2',
      default_requires = ['coreutils']
    )

    ImagesCreator.__init__(self)

    self.DATA = {
      'variables': ['product', 'pva', 'rpm_release'],
      'config':    ['.'],
      'input' :    [],
      'output':    [self.build_folder],
    }

    self.custom_theme = self.build_folder / 'usr/share/%s/custom.conf' % self.rpm_name

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
     'CUSTOM_CONF_DIR=%{_sysconfdir}/gdm',
     'CUSTOM_CONF=$CUSTOM_CONF_DIR/custom.conf',
     'if [ -e $CUSTOM_CONF -a ! -e $CUSTOM_CONF.theme-save ]; then',
     '  %{__mv} $CUSTOM_CONF $CUSTOM_CONF.theme-save',
     '  %%{__cp} %s $CUSTOM_CONF' % custom_conf,
     'fi',
    ])
    return 'gdm', gdm_install_trigger

  def _get_background_install_trigger(self):
    bg_install_trigger = self.build_folder / 'bg-install-trigger.sh'
    lines = ['bg_folder=%{_datadir}/backgrounds']
    for file in ['default.jpg', 'default.png',
                 'default-5_4.png', 'default-wide.png']:
      lines.extend([
        'if [ ! -e $bg_folder/images/%s.theme-save -a -e $bg_folder/images/%s ]; then' % (file, file),
        '  %%{__mv} $bg_folder/images/%s $bg_folder/images/%s.theme-save' % (file, file),
        '  %%{__cp} $bg_folder/spin/2-spin-day.png $bg_folder/images/%s' % file,
        'fi',
      ])

    for dir, xml in [('infinity', 'infinity.xml')]:
      lines.extend([
        'if [ -d $bg_folder/%s -a ! -d $bg_folder/%s.theme-save ]; then' % (dir, dir),
        '  %%{__mv} $bg_folder/%s $bg_folder/%s.theme-save' % (dir, dir),
        '  %%{__ln_s} $bg_folder/spin $bg_folder/%s' % dir,
        '  %%{__ln_s} $bg_folder/spin/spin.xml $bg_folder/spin/%s' % xml,
        'fi',
      ])

    bg_install_trigger.write_lines(lines)
    return 'desktop-backgrounds-basic', bg_install_trigger

  def _get_gdm_uninstall_trigger(self):
    gdm_uninstall_trigger = self.build_folder / 'gdm-uninstall-trigger.sh'
    gdm_uninstall_trigger.write_lines([
      'rm -f %{_sysconfdir}/gdm/custom.conf.theme-save'
    ])
    return 'gdm', gdm_uninstall_trigger

  def _get_background_uninstall_trigger(self):
    bg_uninstall_trigger = self.build_folder / 'bg-uninstall-trigger.sh'
    lines = ['bg_folder=%{_datadir}/backgrounds']
    for file in ['default.jpg', 'default.png',
                 'default-5_4.png', 'default-wide.png']:
      lines.extend([
        '%%{__rm} -f $bg_folder/images/%s' % file,
        '%%{__mv} $bg_folder/images/%s.theme-save $bg_folder/images/%s' % (file, file),
      ])

    for dir, xml in [('infinity', 'infinity.xml')]:
      lines.extend([
        'if [ -d $bg_folder/%s.theme-save ]; then' % dir,
        '  %%{__rm} -f $bg_folder/%s' % dir,
        '  %%{__rm} -f $bg_folder/spin/%s' % xml,
        '  %%{__mv} $bg_folder/%s.theme-save $bg_folder/%s' % (dir, dir),
        'fi',
      ])

    bg_uninstall_trigger.write_lines(lines)
    return 'desktop-backgrounds-basic', bg_uninstall_trigger
