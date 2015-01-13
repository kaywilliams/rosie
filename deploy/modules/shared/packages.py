#
# Copyright (c) 2015
# Deploy Foundation. All rights reserved.
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

from deploy.event     import Event
from deploy.util      import pps

from deploy.modules.shared.rpmbuild import RpmBuildMixin

__all__ = ['PackagesEventMixin']


class PackagesEventMixin(RpmBuildMixin):
  packages_mixin_version = '1.03'

  def __init__(self):
    # self.comes_before.add('packages') # add to deploy module events
    self.provides.update(['user-required-packages', 'excluded-packages',
                          'user-required-groups'])

    if not hasattr(self, 'DATA'): self.DATA = {}
    self.DATA.setdefault('variables', set()).add('packages_mixin_version')
    self.DATA.setdefault('config', set()).update(['exclude', 'group',
                                                  'package'])
    self.DATA.setdefault('input', set())
    self.DATA.setdefault('output', set())

    RpmBuildMixin.__init__(self)

  def setup(self):
    if not self.diff.handlers: self.diff.setup(self.DATA)

    RpmBuildMixin.setup(self)

    self.rpmsdir = self.mddir / 'rpms'
    self.rpmsdir.mkdirs()

    # setup comps groups
    self.cvars.setdefault('user-required-groups', set()).update(
                           self.config.xpath('group', []))

    # setup excluded packages
    self.cvars.setdefault('excluded-packages', set()).update(
                           self.config.xpath('exclude/text()', []))

    # setup packages
    self.cvars.setdefault('user-required-packages', set())
    for x in self.config.xpath("package", []):
      if x.get('dir', None):
        self._setup_rpm_from_path(path=pps.path(x.get('dir')) / x.text,
                                  dest=self.rpmsdir, type='rpm')
      else:
        if x.text.startswith('-'):
          self.cvars['excluded-packages'].add(x.text[1:])
        else:
          self.cvars['user-required-packages'].add(x.text)

  def run(self):
    self.io.process_files(cache=True, callback=self.link_callback, text=None,
                          what='rpm')
    self.rpms = [ self._get_rpmbuild_data(f)
                  for f in self.io.list_output(what='rpm') ]
    RpmBuildMixin.run(self)

  def apply(self):
    RpmBuildMixin.apply(self)
