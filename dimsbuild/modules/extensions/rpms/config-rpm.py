from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event

from dimsbuild.modules.shared import InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['ConfigRpmEvent']}

class ConfigRpmEvent(Event, RpmBuildMixin, InputFilesMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'config-rpm',
      version = 3,
      provides = ['custom-rpms', 'custom-srpms', 'custom-rpms-info']
    )

    RpmBuildMixin.__init__(self,
      '%s-config' % self.product,
      "The %s-config provides scripts and supporting files for configuring "
      "the %s distribution." %(self.product, self.fullname),
      "%s configuration script and supporting files" % self.fullname
    )

    InputFilesMixin.__init__(self)

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
    self.noreplace_ids = []
    self.config_count = 0
    self.support_count = 0

  def setup(self):
    self._setup_build()
    self._setup_download()

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

  def _get_download_id(self, type):
    if type == 'config-files':
      rtn = 'config-files-%d' % self.config_count
      self.config_count += 1
    elif type == 'support-files':
      rtn = 'support-files-%d' % self.support_count
      self.support_count += 1
    else:
      raise RuntimeError("unknown type: '%s'" % type)
    return rtn

  def _handle_attributes(self, id, element, attribs):
    if 'noreplace' in attribs:
      noreplace = element.get('@noreplace', 'False')
      if noreplace in BOOLEANS_TRUE:
        self.noreplace_ids.append(id)

  def _generate(self):
    RpmBuildMixin._generate(self)

    self.io.sync_input(cache=True)

    # generate auto-config file
    config_scripts = []
    for id in [ 'config-files-%d' % i for i in xrange(self.config_count) ]:
      config_scripts.extend(self.io.list_output(id))

    if config_scripts:
      self.auto_script = self.build_folder / 'usr/lib/%s/auto.sh' % self.product
      self.auto_script.write_lines(config_scripts)
      self.auto_script.chmod(0755)

  def _get_post_install_script(self):
    if self.auto_script:
      post_install = self.build_folder / 'post-install.sh'
      post_install.write_lines([
        '/%s' % self.auto_script.relpathfrom(self.build_folder).normpath()
      ])
      return post_install
    return None

  def _add_config_files(self, spec):
    config = []
    noreplace = []
    for id in [ 'support-files-%d' % i for i in xrange(self.support_count) ]:
      files = ['/%s' % x.relpathfrom(self.build_folder) for x in self.io.list_output(id)]
      if id in self.noreplace_ids:
        noreplace.extend(files)
      else:
        config.extend(files)
    if config:
      spec.set('bdist_rpm', 'config_files', '\n\t'.join(config))
    if noreplace:
      spec.set('bdist_rpm', 'config_files_noreplace', '\n\t'.join(noreplace))
