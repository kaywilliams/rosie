SETUP_PY_TEXT = r"""
from ConfigParser      import ConfigParser, NoOptionError
from distutils.command import bdist_rpm, install
from distutils.core    import setup
from distutils.dist    import Distribution
from distutils.errors  import DistutilsOptionError

import os
import os.path
import re
import string
import sys
import types

class RenditionDistribution(Distribution):
  def __init__(self, attrs=None):
    Distribution.__init__(self, attrs=attrs)

  def parse_config_files(self, filenames=None):
    if filenames is None:
      filenames = self.find_config_files()

    parser = ConfigParser()
    for filename in filenames:
      parser.read(filename)
      for section in parser.sections():
        options = parser.options(section)
        opt_dict = self.get_option_dict(section)
        for opt in options:
          if opt != '__name__':
            val = parser.get(section, opt)
            opt = string.replace(opt, '-', '_')
            if section == 'metadata':
              setattr(self.metadata, opt, val)
            elif section == 'distribution':
              method = '_parse_%s' % opt
              if not hasattr(self, method):
                raise DistutilsOptionError("Unhandled '%s' option specified in %s" % \
                                             (filename, opt))
              else:
                val = getattr(self, method)(val)
              setattr(self, opt, val)
            else:
              opt_dict[opt] = (filename, val)

      # Make the ConfigParser forget everything (so we retain
      # the original filenames that options come from)
      parser.__init__()

      # If there was a "global" section in the config file, use it
      # to set Distribution options.

      if self.command_options.has_key('global'):
        for (opt, (src, val)) in self.command_options['global'].items():
          alias = self.negative_opt.get(opt)
          try:
            if alias:
              setattr(self, alias, not strtobool(val))
            elif opt in ('verbose', 'dry_run'): # ugh!
              setattr(self, opt, strtobool(val))
            else:
              setattr(self, opt, val)
          except ValueError, msg:
            raise DistutilsOptionError(msg)

  def _parse_packages(self, value):
    return self._parse_list(value)

  def _parse_package_dir(self, value):
    return self._parse_dict(value)

  def _parse_scripts(self, value):
    return self._parse_list(value)

  def _parse_py_modules(self, value):
    return self._parse_list(value)

  def _parse_package_data(self, value):
    return self._parse_dict(value, multiple=True)

  def _parse_data_files(self, value):
    return self._parse_dict(value, multiple=True, aslist=True)

  def _parse_list(self, value, delim=None):
    delim = delim or '\n'
    return [ x.strip() for x in value.split(delim) ]

  def _parse_dict(self, value, multiple=False, aslist=False):
    rtn = {}
    if multiple:
      pattern = ' *[^\:, \n]+ *:(?: *[^\:, \n ]+ *,)* *[^:, \n]+[ |\n]*'
    else:
      pattern = ' *[^:, \n]+ *: *[^\:, \n]+[ |\n]*'
    regex = re.compile(pattern)
    items = [x.strip() for x in regex.findall(value)]
    for item in items:
      tokens = item.split(':')
      if multiple:
        key = tokens[0].strip()
        value = [x.strip() for x in tokens[1].strip().split(',')]
        rtn.setdefault(key, []).extend(value)
      else:
        rtn[tokens[0].strip()] = tokens[1].strip()
    if aslist:
      return rtn.items()
    return rtn


class Install(install.install):

  def initialize_options(self):
    install.install.initialize_options(self)
    self.optimize = 1
    self.compile = True

  def get_outputs (self):
    # Assemble the outputs of all the sub-command.

    # HACK ALERT: I have to do this because bdist_rpm is insanely
    # stupid about byte-compiled and optimized python code :(.

    bdist_rpm_opts = self.distribution.get_option_dict('bdist_rpm')
    try:
      config_files = bdist_rpm_opts['config_files'][1].split()
    except KeyError:
      config_files = []
    try:
      doc_files = bdist_rpm_opts['doc_files'][1].split()
    except KeyError:
      doc_files = []

    outputs = []
    tocompile = []
    for cmd_name in self.get_sub_commands():
      cmd = self.get_finalized_command(cmd_name)
      # Add the contents of cmd.get_outputs(), ensuring that outputs
      # doesn't contain duplicate entries
      for filename in cmd.get_outputs():
        if filename not in outputs:
          outputs.append(filename)
          if filename.endswith('.py'):
            tocompile.append(os.path.join(self.root, filename))
            filename_pyc = ''.join([filename, 'c'])
            filename_pyo = ''.join([filename, 'o'])
            if filename_pyc not in outputs:
              outputs.append(filename_pyc)
            if filename_pyo not in outputs:
              outputs.append(filename_pyo)
    if self.path_file and self.install_path_file:
      outputs.append(os.path.join(self.install_libbase,
                    self.path_file + ".pth"))

    if tocompile:
      from distutils.util import byte_compile
      if self.compile:
        byte_compile(tocompile, optimize=0)
      if self.optimize:
        byte_compile(tocompile, optimize=self.optimize)

    # filter out config files and doc files from data files
    rtn = []
    for file in outputs:
      config = filter(lambda config: file.endswith(config), config_files)
      doc = filter(lambda doc: file.endswith(doc), doc_files)
      if len(config) == 0 and len(doc) == 0:
        rtn.append(file)
    return rtn


class BdistRpm(bdist_rpm.bdist_rpm):
  bdist_rpm.bdist_rpm.user_options.extend([
    ('config-files=', None, "files that will be added as configuration files"),
    ('config-files-noreplace=', None, "configuration files with noreplace"),
    ('doc-dirs=', None, "directories to be added as documentation directories"),
    ('ghost-files', None, "files that will be installed as ghost files"),
    ('trigger-configs', None, "config files for triggers"),
  ])

  def initialize_options(self):
    bdist_rpm.bdist_rpm.initialize_options(self)
    self.config_files = None
    self.config_files_noreplace = None
    self.doc_dirs = None
    self.ghost_files = None
    self.trigger_configs = None

  def finalize_options(self):
    bdist_rpm.bdist_rpm.finalize_options(self)
    self.ensure_string_list('config_files')
    self.ensure_string_list('config_files_noreplace')
    self.ensure_string_list('doc_dirs')
    self.ensure_string_list('ghost_files')
    self.ensure_string_list('trigger_configs')

    if self.trigger_configs:
      for file in self.trigger_configs:
        assert os.path.isfile(file)

  def run(self):
    bdist_rpm.bdist_rpm.run(self)

  def _make_spec_file(self):
    spec_file = [
      '%%define name %s' % self.distribution.get_name(),
      '%%define version %s' % self.distribution.get_version().replace('-','_'),
      '%%define release %s' % self.release.replace('-','_'),
      '%define  _use_internal_dependency_generator 0',
      '',
      'Summary: %s' % self.distribution.get_description(),
      'Name: %{name}',
      'Version: %{version}',
      'Release: %{release}',
    ]

    if self.use_bzip2:
      spec_file.append('Source0: %{name}-%{version}.tar.bz2')
    else:
      spec_file.append('Source0: %{name}-%{version}.tar.gz')

    spec_file.extend([
      'License: %s' % self.distribution.get_license(),
      'Group: %s' % self.group,
      'BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)',
    ])

    if not self.force_arch:
      # noarch if no extension modules
      if not self.distribution.has_ext_modules():
        spec_file.append('BuildArch: noarch')
    else:
      spec_file.append( 'BuildArch: %s' % self.force_arch )

    for field in ['Packager', 'Provides', 'Requires', 'Conflicts', 'Obsoletes']:
      val = getattr(self, string.lower(field))
      if type(val) is types.ListType:
        spec_file.append('%s: %s' % (field, string.join(val)))
      elif val is not None:
        spec_file.append('%s: %s' % (field, val))

    if self.distribution.get_url() != 'UNKNOWN':
      spec_file.append('Url: ' + self.distribution.get_url())

    if self.distribution_name:
      spec_file.append('Distribution: ' + self.distribution_name)

    if self.build_requires:
      spec_file.append('BuildRequires: ' +
                       string.join(self.build_requires))

    if self.icon:
      spec_file.append('Icon: ' + os.path.basename(self.icon))

    if self.no_autoreq:
      spec_file.append('AutoReq: 0')

    spec_file.extend([
      '',
      '%description',
      self.distribution.get_long_description()
    ])

    def_setup_call = "%s %s" % (self.python, os.path.basename(sys.argv[0]))
    def_build = "%s build" % def_setup_call
    if self.use_rpm_opt_flags:
      def_build = 'env CFLAGS="$RPM_OPT_FLAGS" ' + def_build

    script_options = [
      ('prep', 'prep_script', "%setup -q"),
      ('build', 'build_script', def_build),
      ('install', 'install_script',
       ["rm -rf $RPM_BUILD_ROOT",
        "mkdir -p $RPM_BUILD_ROOT",
        "%s install --root=$RPM_BUILD_ROOT --record=INSTALLEDFILES" % def_setup_call]),
      ('clean', 'clean_script', "rm -rf $RPM_BUILD_ROOT"),
      ('verifyscript', 'verify_script', None),
      ('pre', 'pre_install', None),
      ('post', 'post_install', None),
      ('preun', 'pre_uninstall', None),
      ('postun', 'post_uninstall', None),
    ]

    for (rpm_opt, attr, default) in script_options:
      val = getattr(self, attr)
      if val or default:
        spec_file.extend([
          '',
          '%%%s' % rpm_opt,
        ])
        if val:
          spec_file.extend(string.split(open(val, 'r').read(), '\n'))
        if default:
          if type(default) == type(''):
            spec_file.append(default)
          else:
            spec_file.extend(default)

    if self.trigger_configs:
      defaults = {
        'triggerin_scripts':     '',
        'triggerun_scripts':     '',
        'triggerpostun_scripts': '',
        'triggerin_flags':       '',
        'triggerun_flags':       '',
        'triggerpostun_flags':   '',
      }
      for config in self.trigger_configs:
        parser = ConfigParser(defaults)
        parser.read(config)
        for section in parser.sections():
          trigger = parser.get(section, 'triggerid') or section
          for rpm_option in ['triggerin', 'triggerun', 'triggerpostun']:
            script_files = parser.get(section, '%s_scripts' % rpm_option) or None
            script_flags = parser.get(section, '%s_flags'   % rpm_option) or None
            contents = []
            if script_files is not None:
              script_files = re.split(r',\s*|\s+', script_files)
            else:
              script_files = []
            for file in script_files:
              if not os.path.isfile(file):
                raise DistutilsOptionError("'%s' does not exist or is not a file" % \
                                           file)
              f = open(file, 'r')
              contents.extend([x.strip('\n') for x in f.readlines()])
              f.close()
            if contents:
              if script_flags:
                spec_file.extend([
                  '',
                  '%%%s %s -- %s' % (rpm_option, script_flags, trigger)
                ])
              else:
                spec_file.extend([
                  '',
                  '%%%s -- %s' % (rpm_option, trigger)
                ])
              for line in contents:
                spec_file.append(line)

    ## write %files section
    spec_file.extend([
      '',
      '%files -f INSTALLEDFILES',
      '%defattr(-,root,root)',
    ])
    if self.doc_files:
      for doc in self.doc_files:
        spec_file.append('%%doc %s' % doc)
    if self.config_files:
      for config_file in self.config_files:
        spec_file.append('%%config %s' % config_file)
    if self.config_files_noreplace:
      for config_file in self.config_files_noreplace:
        spec_file.append('%%config %s' % config_file)
    if self.ghost_files:
      for ghost_file in self.ghost_files:
        spec_file.append('%%ghost %s' % ghost_file)
    if self.doc_dirs:
      for doc_dir in self.doc_dirs:
        spec_file.append('%%docdir %s' % doc_dir)
    ## done writing %files section

    if self.changelog:
      spec_file.extend([
          '',
          '%changelog',
      ])
      spec_file.extend(self.changelog)

    return spec_file

def main():
  attrs = {
    'distclass': RenditionDistribution,
    'cmdclass':  {
      'install':   Install,
      'bdist_rpm': BdistRpm,
    },
  }
  setup(**attrs)

if __name__ == "__main__":
  main()
"""
