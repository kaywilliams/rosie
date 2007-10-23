from dims import pps

from dimsbuild.event import Event

from dimsbuild.modules.shared import InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0

class ConfigRpmEvent(Event, RpmBuildMixin, InputFilesMixin):
  def __init__(self):
    Event.__init__(self, id='config-rpm',
                   provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info'])
    RpmBuildMixin.__init__(self,
                           '%s-config' % self.product,
                           'The %s-config provides scripts and supporting '\
                           'files for configuring the %s '\
                           'distribution.' %(self.product, self.fullname),
                           '%s configuration script and supporting files' % self.fullname)
    InputFilesMixin.__init__(self)

    self.build_folder = self.mddir / 'build'

    self.installinfo = {
      'config' : ('config/script', '/usr/lib/%s' % self.product, '755'),
      'support': ('config/supporting-files/path', '/usr/lib/%s' % self.product, None)
    }

    self.DATA = {
      'variables': ['product', 'fullname', 'pva'],
      'config':    ['.'],
      'input':     [],
      'output':    [self.build_folder],
    }

  def setup(self):
    self._setup_build()
    self._setup_download()

  def check(self):
    return self.release == '0' or \
           not self.autofile.exists() or \
           self.diff.test_diffs()

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
    self.cvars.setdefault('custom-rpms-info', []).append((self.rpmname, 'mandatory', None, self.obsoletes, None))

  def _generate(self):
    self.io.sync_input(cache=True)

  def _get_files(self):
    sources = {}
    sources.update(RpmBuildMixin._get_files(self))
    sources.update(InputFilesMixin._get_files(self))
    return sources

  def _test_build(self, default):
    if RpmBuildMixin._test_build(self, default):
      if self.config.get('requires', None) or \
         self.config.get('obsoletes', None) or \
         self.config.get('config/script/path/text()', None) or \
         self.config.get('config/supporting-files/path/text()', None):
        return True
    return False

  def _getpscript(self):
    post_install_scripts = self.io.list_output(what=self.installinfo['config'])
    try:
      (self.build_folder/'post-install.sh').write_lines(
        [ post_install_scripts[0].relpathfrom(self.rpmdir).normpath() ])
      return self.build_folder/'post-install.sh'
    except IndexError:
      return None

EVENTS = {'rpms': [ConfigRpmEvent]}
