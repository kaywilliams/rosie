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

from spin.event     import Event
from spin.locals    import L_LOGOS_RPM_APPLIANCE_INFO

from spin.modules.shared import RpmBuildMixin, Trigger, TriggerContainer

from files import FilesHandlerMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['LogosRpmEvent'],
  description = 'creates a logos RPM',
  group       = 'rpmbuild',
)

class LogosRpmEvent(FilesHandlerMixin, RpmBuildMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'logos-rpm',
      parentid = 'rpmbuild',
      version = '0.1.2',
      requires = ['base-info', 'anaconda-version', 'logos-versions'],
      provides = ['rpmbuild-data']
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

    FilesHandlerMixin.__init__(self)

    self.DATA = {
      'config': ['.'],
      'variables': ['applianceid', 'fullname', 'copyright', 'rpm.release',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'logos-versions\']'],
      'output': [self.rpm.build_folder],
      'input':  [],
    }

    self._appliance_info = None

  @property
  def appliance_info(self):
    if not self._appliance_info:
      try:
        self._appliance_info = self.locals.L_LOGOS_RPM_APPLIANCE_INFO
      except KeyError:
        fullname = self.cvars['base-info']['fullname']
        version  = self.cvars['base-info']['version']
        # See if the version of the input distribution is a bugfix
        found = False
        if L_LOGOS_RPM_APPLIANCE_INFO.has_key(fullname):
          for ver in L_LOGOS_RPM_INFO[fullname]:
            if version.startswith(ver):
              found = True
              self._appliance_info = L_LOGOS_RPM_APPLIANCE_INFO[fullname][ver]
              break
        if not found:
          # if not one of the "officially" supported appliances, default
          # to something
          self._appliance_info = L_LOGOS_RPM_INFO['*']['0']
    return self._appliance_info

  def setup(self):
    obsoletes = [ '%s %s %s' %(n,e,v)
                  for n,e,v in self.cvars.get('logos-versions', [])]
    provides = [ 'system-logos %s %s' % (e,v)
                 for _,e,v in self.cvars.get('logos-versions', [])]
    self.rpm.setup_build(obsoletes=obsoletes, provides=provides)
    self.fh.setup()

  def generate(self):
    RpmBuildMixin.generate(self)
    if len(self.fh.files) == 0:
      raise RuntimeError("No images found in any share path: %s" %
                         listfmt.format(self.SHARE_DIRS,
                           pre='\'', post='\'', sep=', ', last=', '))
    self.fh.generate()
    self._generate_custom_theme()

  def get_post(self):
    if not self.appliance_info.has_key('post-install'):
      return None
    post_install = self.rpm.build_folder / 'post-install.sh'
    post_install.write_text(self.appliance_info['post-install'])
    return post_install

  def get_postun(self):
    if not self.appliance_info.has_key('post-uninstall'):
      return None
    post_uninstall = self.rpm.build_folder / 'post-uninstall.sh'
    post_uninstall.write_text(self.appliance_info['post-uninstall'])
    return post_uninstall

  def get_triggers(self):
    triggers = TriggerContainer()
    for triggerid in self.appliance_info.get('triggers', {}):
      trigger = Trigger(triggerid)
      triggerin = self.appliance_info['triggers'][triggerid].get('triggerin', None)
      if triggerin is not None:
        script = self.rpm.build_folder / '%s-triggerin.sh' % triggerid
        script.write_text(triggerin % {'rpm_name': self.rpm.name})
        trigger.setdefault('triggerin_scripts', []).append(script)
      triggerun = self.appliance_info['triggers'][triggerid].get('triggerun', None)
      if triggerun is not None:
        script = self.rpm.build_folder / '%s-triggerun.sh' % triggerid
        script.write_text(triggerun % {'rpm_name': self.rpm.name})
        trigger.setdefault('triggerun_scripts', []).append(script)
      triggers.append(trigger)
    return triggers

  def _generate_custom_theme(self):
    custom_theme = self.rpm.build_folder / 'usr/share/%s/custom.conf' % self.rpm.name
    custom_theme.dirname.mkdirs()
    custom_theme.write_text(
      self.locals.L_GDM_CUSTOM_THEME % \
      {'themename': self.config.get('theme/text()', 'Spin')}
    )
