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
import gzip

from rendition import listfmt
from rendition import shlib

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event
from spin.locals    import L_LOGOS_RPM_INFO

from spin.modules.shared import RpmBuildMixin, Trigger, TriggerContainer

from constants import *
from handlers  import *

API_VERSION = 5.0

EVENTS = ['LogosRpmEvent']

class LogosRpmEvent(RpmBuildMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'logos-rpm',
      parentid = 'rpms',
      version = '1.0',
      requires = ['base-info', 'anaconda-version', 'logos-versions'],
      provides = ['custom-rpms-data']
    )

    RpmBuildMixin.__init__(self,
      '%s-logos' % self.name,
      "The %s-logos package contains image files which have been automatically "
      "created by spin and are specific to %s." % (self.name, self.fullname),
      "Icons and pictures related to %s" % self.fullname,
      license = 'GPLv2',
      provides = ['system-logos'],
      requires = ['coreutils'],
    )

    self.handlers = []

    self.DATA = {
      'config': ['.'],
      'variables': ['distroid', 'fullname', 'copyright', 'rpm.release',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'logos-versions\']'],
      'output': [self.rpm.build_folder],
      'input':  [],
    }

    self._distro_info = None

  def setup(self):
    obsoletes = [ '%s %s %s' %(n,e,v)
                  for n,e,v in self.cvars.get('logos-versions', [])]
    provides = [ 'system-logos %s %s' % (e,v)
                 for _,e,v in self.cvars.get('logos-versions', [])]
    self.rpm.setup_build(obsoletes=obsoletes, provides=provides)
    self._setup_handlers()

  def generate(self):
    RpmBuildMixin.generate(self)
    for handler in self.handlers:
      handler.generate()
    if len(self.rpm.data_files) == 0:
      raise RuntimeError("No images found in any share path: %s" %
                         listfmt.format(self.SHARE_DIRS,
                           pre='\'', post='\'', sep=', ', last=', '))
    self._generate_custom_theme()

  def _generate_custom_theme(self):
    custom_theme = self.rpm.build_folder / 'usr/share/%s/custom.conf' % self.rpm.name
    custom_theme.dirname.mkdirs()
    custom_theme.write_text(
      self.locals.L_GDM_CUSTOM_THEME % \
      {'themename': self.config.get('theme/text()', 'Spin')}
    )

  def get_post(self):
    if not self.distro_info.has_key('post-install'):
      return None
    post_install = self.rpm.build_folder / 'post-install.sh'
    post_install.write_text(self.distro_info['post-install'])
    return post_install

  def get_postun(self):
    if not self.distro_info.has_key('post-uninstall'):
      return None
    post_uninstall = self.rpm.build_folder / 'post-uninstall.sh'
    post_uninstall.write_text(self.distro_info['post-uninstall'])
    return post_uninstall

  def get_triggers(self):
    triggers = TriggerContainer()
    for target, content in self.distro_info.get('triggerin', {}).items():
      script = self.rpm.build_folder / '%s-triggerin.sh' % target
      script.write_text(content % {'rpm_name': self.rpm.name})
      triggers.append(Trigger(target, triggerin_scripts=[script]))
    for target, content in self.distro_info.get('triggerun', {}).items():
      script = self.rpm.build_folder / '%s-triggerun.sh' % target
      script.write_text(content % {'rpm_name': self.rpm.name})
      triggers.append(Trigger(target, triggerun_scripts=[script]))
    return triggers

  def _setup_handlers(self):
    supplied_logos = self.config.get('logos-path/text()', None)
    distro_paths   = self._get_handler_paths(self.distro_info['folder'])

    required_xwindow = self.config.get('include-xwindows-art/text()', 'all').lower()
    xwindow_types    = XWINDOW_MAPPING[required_xwindow]
    write_text       = self.config.get('write-text/text()', 'True') in BOOLEANS_TRUE

    if supplied_logos:
      self.DATA['input'].append(supplied_logos)
      ## FIXME: not writing text to user-specified images
      self.handlers.append(SuppliedFilesHandler(self, [supplied_logos], False))

    self.handlers.append(DistroFilesHandler(self, distro_paths,
                                            write_text, xwindow_types,
                                            self.distro_info['start_color'],
                                            self.distro_info['end_color']))

  def _get_handler_paths(self, distro_folder):
    # setup distro-specific, common files, and fallback handlers
    distro_paths = []
    for shared_dir in [ x / 'logos-rpm' for x in self.SHARE_DIRS ]:
      distro = shared_dir / 'distros' / distro_folder
      if distro.exists(): distro_paths.append(distro)
    return distro_paths

  @property
  def distro_info(self):
    if not self._distro_info:
      try:
        self._distro_info = self.locals.L_LOGOS_RPM_INFO
      except KeyError:
        fullname = self.cvars['base-info']['fullname']
        version  = self.cvars['base-info']['version']
        # See if the version of the input distribution is a bugfix
        found = False
        if L_LOGOS_RPM_INFO.has_key(fullname):
          for ver in L_LOGOS_RPM_INFO[fullname]:
            if version.startswith(ver):
              found = True
              self._distro_info = L_LOGOS_RPM_INFO[fullname][ver]
              break
        if not found:
          # if not one of the "officially" supported distros, default
          # to something
          self._distro_info = L_LOGOS_RPM_INFO['*']['0']
    return self._distro_info
