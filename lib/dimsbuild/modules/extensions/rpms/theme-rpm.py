from dimsbuild.event import Event

from dimsbuild.modules.shared.rpms import RpmBuildMixin

API_VERSION = 5.0

class ThemeRpmEvent(Event, RpmBuildMixin):
  def __init__(self):
    self.themename = \
      self.config.get('/distro/theme-rpm/theme/text()', self.product)

    self.DATA = {
      'variables': ['product', 'pva'],
      'config':    ['/distro/theme-rpm'],
      'input' :    [],
      'output':    [],
    }

    Event.__init__(self, id='theme-rpm',
                   provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info'])
    RpmBuildMixin.__init__(self,
                           '%s-theme' % self.product,
                           'The %s-theme package requires the gdm package. '\
                           'Its sole function is to modify the value of the GraphicalTheme '\
                           'attribute in /usr/share/gdm/defaults.conf to the %s '
                           'theme.' %(self.product, self.themename),
                           'Script to set default gdm graphical theme',
                           defrequires='gdm')
  def error(self, e):
    self.build_folder.rm(recursive=True, force=True)

  def setup(self):
    self._setup_build()

  def validate(self):
    self.validator.validate('/distro/theme-rpm', 'theme-rpm.rng')

  def run(self):
    self.io.clean_eventcache(all=True)
    if self._test_build('True'):
      self._build_rpm()
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    if not self._test_build('True'):
      return
    self._check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []
    self.cvars['custom-rpms-info'].append((self.rpmname, 'conditional', 'gdm', self.obsoletes))

  def _getpscript(self):
    f = (self.build_folder/'postinstall.sh').open('w')
    f.write(self.locals.default_theme % {'themename': self.themename})
    f.close()
    return 'postinstall.sh'


EVENTS = {'RPMS': [ThemeRpmEvent]}
