from rendition import pps

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event

from spin.modules.shared import InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['ConfigRpmEvent']}

class ConfigRpmEvent(Event, RpmBuildMixin, InputFilesMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'config-rpm',
      version = 4,
      provides = ['custom-rpms', 'custom-srpms', 'custom-rpms-info']
    )

    RpmBuildMixin.__init__(self,
      '%s-config' % self.product,
      "The %s-config provides scripts and supporting files for configuring "
      "the %s distribution." %(self.product, self.fullname),
      "%s configuration script and supporting files" % self.fullname,
      default_requires = ['coreutils']
    )

    InputFilesMixin.__init__(self, {
      'scripts' : ('script', '/usr/lib/%s' % self.product, '755', True),
      'files': ('file', '/usr/share/%s/files' % self.product, None, False)
    })

    self.DATA = {
      'variables': ['product', 'fullname', 'pva', 'rpm_release'],
      'config':    ['.'],
      'input':     [],
      'output':    [self.build_folder],
    }

    self.auto_script = None
    self.script_count = 0
    self.files_count = 0

    self.support_ids = []

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
    if type == 'scripts':
      rtn = 'scripts-%d' % self.script_count
      self.script_count += 1
    elif type == 'files':
      rtn = 'files-%d' % self.files_count
      self.files_count += 1
    else:
      raise RuntimeError("unknown type: '%s'" % type)
    return rtn

  def _handle_attributes(self, id, item, attribs):
    if 'dest' in attribs:
      self.support_ids.append(id)

  def _generate(self):
    RpmBuildMixin._generate(self)

    self.io.sync_input(cache=True)

    # generate auto-config file
    config_scripts = []
    for id in [ 'scripts-%d' % i for i in xrange(self.script_count) ]:
      for path in self.io.list_output(id):
        config_scripts.append('/' / path.relpathfrom(self.build_folder))

    if config_scripts:
      self.auto_script = self.build_folder / 'usr/lib/%s/auto.sh' % self.product
      self.auto_script.dirname.mkdirs()
      self.auto_script.write_lines(config_scripts)
      self.auto_script.chmod(0755)

  def _get_post_install_script(self):
    lines = []
    if self.auto_script:
      lines.append('/%s' % self.auto_script.relpathfrom(self.build_folder).normpath())

    # move support files as needed
    if self.support_ids:
      for id in self.support_ids:
        for support_file in self.io.list_output(id):
          src = P('/%s') % support_file.relpathfrom(self.build_folder).normpath()
          dst = P('/%s') % src.relpathfrom(self.install_info['files'][1]).normpath()
          dir = dst.dirname
          lines.extend([
            'if [ -e %s ]; then' % dst,
            '  %%{__mv} %s %s.config-save' % (dst, dst),
            'fi',
            'if [ ! -d %s ]; then' % dir,
            '  %%{__mkdir} -p %s' % dir,
            'fi',
            '%%{__mv} %s %s' % (src, dst)
          ])

    if lines:
      post_install = self.build_folder / 'post-install.sh'
      post_install.write_lines(lines)
      return post_install
    return None

  def _get_post_uninstall_script(self):
    lines = []
    if self.support_ids:
      for id in self.support_ids:
        for support_file in self.io.list_output(id):
          src = P('/%s') % support_file.relpathfrom(self.build_folder).normpath()
          dst = P('/%s') % src.relpathfrom(self.install_info['files'][1]).normpath()
          lines.extend([
            'if [ -e %s.config-save ]; then' % dst,
            '  %%{__mv} -f %s.config-save %s' % (dst, dst),
            'else',
            '  %%{__rm} -f %s' % dst,
            'fi',
          ])

    if lines:
      post_uninstall = self.build_folder / 'post-uninstall.sh'
      post_uninstall.write_lines(lines)
      return post_uninstall
    return None

