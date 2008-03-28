#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
from rendition import pps

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event

from spin.modules.shared import InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0

EVENTS = {'rpms': ['ConfigRpmEvent']}

class ConfigRpmEvent(RpmBuildMixin, Event, InputFilesMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'config-rpm',
      version = '0.91',
      provides = ['custom-rpms-data']
    )

    self.scriptdir = '/usr/lib/%s' % self.product
    self.filedir   = '/usr/share/%s/files' % self.product

    RpmBuildMixin.__init__(self,
      '%s-config' % self.product,
      "The %s-config provides scripts and supporting files for configuring "
      "the %s distribution." %(self.product, self.fullname),
      "%s configuration script and supporting files" % self.fullname,
      default_requires = ['coreutils', 'policycoreutils']
    )

    InputFilesMixin.__init__(self, {
      'scripts' : ('script', self.scriptdir, '755', True),
      'files': ('file', self.filedir, None, False)
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
      self.auto_script.write_lines(['export CFGRPM_SCRIPTS=%s' % self.scriptdir,
                                    'export CFGRPM_FILES=%s' % self.filedir])
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
            '  %%{__mv} %s %s.rpmsave' % (dst, dst),
            'fi',
            'if [ ! -d %s ]; then' % dir,
            '  %%{__mkdir} -p %s' % dir,
            'fi',
            '%%{__mv} %s %s' % (src, dst),
            '/sbin/restorecon %s' % dst,
          ])

    if lines:
      post_install = self.build_folder / 'post-install.sh'
      post_install.write_lines(lines)
      return post_install
    return None

  def _get_post_uninstall_script(self):
    lines = []
    if self.support_ids:
      lines.append('if [ "$1" == "0" ]; then')
      for id in self.support_ids:
        for support_file in self.io.list_output(id):
          src = P('/%s') % support_file.relpathfrom(self.build_folder).normpath()
          dst = P('/%s') % src.relpathfrom(self.install_info['files'][1]).normpath()
          lines.extend([
            '  if [ -e %s.rpmsave ]; then' % dst,
            '    %%{__mv} -f %s.rpmsave %s' % (dst, dst),
            '  else',
            '    %%{__rm} -f %s' % dst,
            '  fi',
          ])
      lines.append('fi')

    if lines:
      post_uninstall = self.build_folder / 'post-uninstall.sh'
      post_uninstall.write_lines(lines)
      return post_uninstall
    return None

