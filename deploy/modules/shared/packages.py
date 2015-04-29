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
    if not hasattr(self, 'DATA'): self.DATA = {}

    self.DATA.setdefault('variables', set()).add('packages_mixin_version')
    self.DATA.setdefault('config', set()).update(['package'])
    self.DATA.setdefault('input', set())
    self.DATA.setdefault('output', set())

    RpmBuildMixin.__init__(self)

  def setup(self):
    if not self.diff.handlers: self.diff.setup(self.DATA)

    RpmBuildMixin.setup(self)

    self.rpmsdir = self.mddir / 'rpms'
    self.rpmsdir.mkdirs()

    # setup user-required groups
    self.user_required_groups.update(self.config.xpath('group', []))

    # setup excluded packages
    self.excluded_packages.update(self.config.xpath('exclude/text()', []))

    # setup user-required packages
    for x in self.config.xpath("package", []):
      group = x.get('group', self.default_groupid)
      if x.get('dir', None):
        self._setup_rpm_from_path(path=pps.path(x.get('dir')) / x.text, 
                                  dest=self.rpmsdir, 
                                  type='rpm')
        self.user_required_packages[x.text] = group
      else:
        if x.text.startswith('-'):
          self.excluded_packages.add(x.text[1:])
        else:
          self.user_required_packages[x.text] = group

  def run(self):
    self.io.process_files(cache=True, callback=self.link_callback, text=None,
                          what='rpm')

    # get data for downloaded rpms
    self.rpms = [ self._get_rpmbuild_data(f)
                  for f in self.io.list_output(what='rpm') ]

    # sign downloaded packages, cache package data
    RpmBuildMixin.run(self)
