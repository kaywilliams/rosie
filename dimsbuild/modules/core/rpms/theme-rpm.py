from dims import pps

from dimsbuild.event import Event

from dimsbuild.modules.shared import RpmBuildMixin

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['ThemeRpmEvent']}

class ThemeRpmEvent(Event, RpmBuildMixin):
  def __init__(self):
    self.themename = self.config.get('theme/text()', 'Spin')

    Event.__init__(self,
      id = 'theme-rpm',
      version = 2,
      provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info']
    )

    RpmBuildMixin.__init__(self,
      '%s-theme' % self.product,
      "Set up the theme of the machine",
      "Theme files related to %s" % self.fullname,
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
      self.copy(image_file, dest.dirname)

  def _generate_custom_theme(self):
    self.custom_theme.dirname.mkdirs()
    self.custom_theme.write_text(
      self.locals.gdm_custom_theme % {'themename': self.themename}
    )

  def _get_install_script(self):
    symlinks=['default.jpg','default.png','default-wide.png','default-5_4.png']
    linklines = ['ln -sf ../infinity/2-infinity-day.png %s' % i for i in symlinks]

    scriptfile = self.build_folder / 'install.sh'
    scriptfile.write_lines([
      'python setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES',
      '# create links to infinity background images',
      'mkdir -p $RPM_BUILD_ROOT%{_datadir}/backgrounds/images',
      '(cd $RPM_BUILD_ROOT%{_datadir}/backgrounds/images;' +
           '; '.join(linklines) + ')',])
    for i in symlinks:
      scriptfile.write_lines([
        'echo %%{_datadir}/backgrounds/images/%s >> INSTALLED_FILES' % i],
        append=True,)
    return scriptfile

  def _get_triggerin(self):
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
    return ['%s:%s' % (target, gdm_install_trigger)]
