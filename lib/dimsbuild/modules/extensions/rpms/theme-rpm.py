from dimsbuild.event import Event

from dimsbuild.modules.shared import RpmBuildMixin

API_VERSION = 5.0
EVENTS = {'rpms': ['ThemeRpmEvent']}

class ThemeRpmEvent(Event, RpmBuildMixin):
  def __init__(self):
    Event.__init__(self, id='theme-rpm',
                   provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info'])

    self.themename = \
      self.config.get('theme/text()', self.product)

    self.build_folder = self.mddir / 'build'

    self.DATA = {
      'variables': ['product', 'pva', 'rpm_release'],
      'config':    ['.'],
      'input' :    [],
      'output':    [self.build_folder],
    }

    RpmBuildMixin.__init__(self,
                           '%s-theme' % self.product,
                           'The %s-theme package requires the gdm package. '\
                           'Its sole function is to modify the value of the GraphicalTheme '\
                           'attribute in /usr/share/gdm/defaults.conf to the %s '
                           'theme.' %(self.product, self.themename),
                           'Script to set default gdm graphical theme',
                           default_requires=['gdm'])

  def setup(self):
    self._setup_build()

  def check(self):
    return self.rpm_release == '0' or \
           not self.autofile.exists() or \
           self.diff.test_diffs()

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

  def _getpscript(self):
    f = (self.build_folder/'postinstall.sh').open('w')
    f.write(self.locals.default_theme % {'themename': self.themename})
    f.close()
    return 'postinstall.sh'
