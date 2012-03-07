#
# Copyright (c) 2011
# CentOS Solutions, Inc. All rights reserved.
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

from centosstudio.event          import Event
from centosstudio.modules.shared import ReleaseRpmEventMixin


def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['ReleaseRpmEvent'],
    description = 'creates a release RPM',
    group       = 'rpmbuild',
  )

class ReleaseRpmEvent(ReleaseRpmEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'release-rpm',
      parentid = 'rpmbuild',
      ptr = ptr,
      version = '1.00',
      provides = ['rpmbuild-data', 'gpgkeys',
                  'gpgcheck-enabled', 'os-content'],
      requires = ['publish-setup-options'],
    )

    self.DATA = {
      'variables': ['name', 'fullname', 'rpm.release',],
      'config':    [], # set by ReleaseRpmEventMixin
      'input':     [],
      'output':    [],
    }

    ReleaseRpmEventMixin.__init__(self) 

  def setup(self):
    ReleaseRpmEventMixin.setup(self, 
      webpath=self.cvars['publish-setup-options']['webpath'])

  def run(self):
    ReleaseRpmEventMixin.run(self)

  def apply(self):
    ReleaseRpmEventMixin.apply(self)
