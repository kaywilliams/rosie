from rendition import pps

from spin.event import Event

from spin.modules.shared import RpmBuildMixin

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['ThemeRpmEvent']}

class ThemeRpmEvent(Event, RpmBuildMixin):
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

    self.DATA = {
      'variables': ['product', 'pva', 'rpm_release'],
      'config':    ['.'],
      'input' :    [],
      'output':    [self.build_folder],
    }

    self.custom_theme = self.build_folder / 'usr/share/%s/custom.conf' % self.rpm_name

  def setup(self):
    self._setup_build()

    # find the themes/ directory to use
    ## TODO - make this a shared function that both logos and themes rpms use
    self.theme_dir = None
    for path in self.SHARE_DIRS:
      theme_dir = path / 'theme'
      if theme_dir.exists():
        self.theme_dir = theme_dir
    if self.theme_dir is None:
      raise RuntimeError("Unable to find themes/ directory in share path(s) '%s'" % \
                         self.SHARE_DIRS)

  def run(self):
    self.io.clean_eventcache(all=True)
    self._build_rpm()
    self.DATA['output'].append(self.bdist_base)
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
    for image_file in self.theme_dir.findpaths(type=pps.constants.TYPE_NOT_DIR):
      relpath = image_file.relpathfrom(self.theme_dir)
      dest = self.build_folder / relpath
      dest.dirname.mkdirs()
      self.link(image_file, dest.dirname)

  def _generate_custom_theme(self):
    self.custom_theme.dirname.mkdirs()
    self.custom_theme.write_text(
      self.locals.gdm_custom_theme % {'themename': self.themename}
    )

  def _get_triggerin(self):
    target1, script1 = self._get_gdm_install_trigger()
    target2, script2 = self._get_gconf_install_trigger()
    return ['%s:%s' % (target1, script1),
            '%s:%s' % (target2, script2)]

  def _get_triggerpostun(self):
    target1, script1 = self._get_gdm_uninstall_trigger()
    target2, script2 = self._get_gconf_uninstall_trigger()
    return ['%s:%s' % (target1, script1),
            '%s:%s' % (target2, script2)]

  def _get_gdm_install_trigger(self):
    target = 'gdm'
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
    return target, gdm_install_trigger

  def _get_gconf_install_trigger(self):
    target = 'GConf2'
    gconf_install_trigger = self.build_folder / 'gconf-install-trigger.sh'
    gconf_install_trigger.write_lines([
      'conf_file=%{_sysconfdir}/gconf/gconf.xml.defaults/%gconf-tree.xml',
      '%{__mv} $conf_file $conf_file.theme-save',
      'sed -i "s/\/usr\/share\/backgrounds\/images\/default.jpg/\/usr\/share\/backgrounds\/spin\/2-spin-day.png/g" $conf_file',
      'sed -i "s/\/usr\/share\/backgrounds\/infinity\/infinity.xml/\/usr\/share\/backgrounds\/spin\/spin.xml/g" $conf_file',
    ])
    return target, gconf_install_trigger

  def _get_gdm_uninstall_trigger(self):
    target = 'gdm'
    gdm_uninstall_trigger = self.build_folder / 'gdm-uninstall-trigger.sh'
    gdm_uninstall_trigger.write_lines([
      'rm -f %{_sysconfdir}/gdm/custom.conf.theme-save'
    ])
    return target, gdm_uninstall_trigger

  def _get_gconf_uninstall_trigger(self):
    trigger = 'GConf2'
    gconf_uninstall_trigger = self.build_folder / 'gconf-uninstall-trigger.sh'
    gconf_uninstall_trigger.write_lines([
      'rm -f %{_sysconfdir}/gconf/gconf.xml.defaults/%gconf-tree.xml.theme-save'
    ])
    return trigger, gconf_uninstall_trigger
