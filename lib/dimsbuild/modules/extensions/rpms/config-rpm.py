from dims import pps

from dimsbuild.event import Event

from dimsbuild.modules.shared import InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0
EVENTS = {'rpms': ['ConfigRpmEvent']}

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
      'variables': ['product', 'fullname', 'pva', 'rpm_release'],
      'config':    ['.'],
      'input':     [],
      'output':    [self.build_folder],
    }

  def setup(self):
    self._setup_build()
    self._setup_download()

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
      (self.rpm_name, 'mandatory', None, self.rpm_obsoletes, None)
    )

  def _generate(self):
    self.io.sync_input(cache=True)

  def _get_files(self):
    sources = {}
    sources.update(RpmBuildMixin._get_files(self))
    sources.update(InputFilesMixin._get_files(self))
    return sources

  def _getpscript(self):
    post_install_scripts = self.io.list_output(what=self.installinfo['config'])
    try:
      (self.build_folder/'post-install.sh').write_lines(
        [ post_install_scripts[0].relpathfrom(self.rpm_dir).normpath() ])
      return self.build_folder/'post-install.sh'
    except IndexError:
      return None
