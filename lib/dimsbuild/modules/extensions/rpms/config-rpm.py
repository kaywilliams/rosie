from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event

from dimsbuild.modules.shared import InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0
EVENTS = {'rpms': ['ConfigRpmEvent']}

class ConfigRpmEvent(Event, RpmBuildMixin, InputFilesMixin):
  def __init__(self):
    Event.__init__(self, id='config-rpm', version=2,
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
      'config-files' : ('script', '/usr/lib/%s' % self.product, '755'),
      'support-files': ('file', '/usr/lib/%s' % self.product, None)
    }

    self.DATA = {
      'variables': ['product', 'fullname', 'pva', 'rpm_release'],
      'config':    ['.'],
      'input':     [],
      'output':    [self.build_folder],
    }

    self.auto_script = None

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

    # generate auto-config file
    config_scripts = []
    xpath, dstdir, _ = self.installinfo['config-files']
    if self.config.pathexists(xpath):
      for item in self.config.xpath(xpath, []):
        src = P(item.get('text()'))
        dst = P(dstdir) / P(item.get('@dest', ''))
        for file in src.findpaths(type=pps.constants.TYPE_NOT_DIR):
          config_scripts.append((dst / file.tokens[len(src.tokens)-1:]).normpath())

    if config_scripts:
      self.auto_script = self.rpm_dir / 'usr/lib/%s/auto.sh' % self.product
      self.auto_script.write_lines(config_scripts)
      self.auto_script.chmod(0755)
      self.DATA['output'].append(self.auto_script)

  def _get_files(self):
    sources = {}
    sources.update(RpmBuildMixin._get_files(self))
    sources.update(InputFilesMixin._get_files(self))
    return sources

  def _getpscript(self):
    if self.auto_script:
      post_install = self.build_folder / 'post-install.sh'
      post_install.write_lines([
        '/%s' % self.auto_script.relpathfrom(self.rpm_dir).normpath()
      ])
      return post_install
    return None

  def _add_files(self, spec):
    # write the list of files to be installed and where they should be installed
    data_files = self._get_files()
    if not data_files:
      return

    value = []
    for installdir, files in data_files.items():
      value.append('%s : %s' %(installdir, ', '.join(files)))
    spec.set('pkg_data', 'data_files', '\n\t'.join(value))

    # mark config files
    config = []
    noreplace = []
    xpath, dstdir, _ = self.installinfo['support-files']
    if self.config.pathexists(xpath):
      for item in self.config.xpath(xpath, []):
        src = P(item.get('text()'))
        dst = P(dstdir) / P(item.get('@dest', ''))
        nrp = item.get('@noreplace', 'False')
        for file in src.findpaths(type=pps.constants.TYPE_NOT_DIR):
          if nrp in BOOLEANS_TRUE:
            noreplace.append((dst / file.tokens[len(src.tokens)-1:]).normpath())
          else:
            config.append((dst / file.tokens[len(src.tokens)-1:]).normpath())

    if config:
      spec.set('bdist_rpm', 'config_files', '\n\t'.join(config))
    if noreplace:
      spec.set('bdist_rpm', 'config_files_noreplace', '\n\t'.join(noreplace))

    # mark files to be installed in '/usr/share/doc' as doc files
    doc_files = []
    for installdir in data_files.keys():
      if installdir.startswith('/usr/share/doc'):
        doc_files.extend([ installdir/x.basename for x in data_files[installdir] ])
    if doc_files:
      spec.set('bdist_rpm', 'doc_files', '\n\t'.join(doc_files))
