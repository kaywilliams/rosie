#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
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

from centosstudio.event                 import Event
from centosstudio.modules.shared.config import ConfigRpmEventMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ConfigRpmEvent'],
  description = 'creates a configuration RPM',
  group       = 'rpmbuild',
)

class ConfigRpmEvent(ConfigRpmEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'config-rpm',
      parentid = 'rpmbuild',
      version = '1.27',
      provides = ['rpmbuild-data'],
    )

    self.DATA = {
      'variables': ['name', 'fullname', 'rpm.release',],
      'config':    [], # set by ConfigRpmEventMixin
      'input':     [],
      'output':    [],
    }

    ConfigRpmEventMixin.__init__(self) 

  def setup(self):
    ConfigRpmEventMixin.setup(self)

  def run(self):
    ConfigRpmEventMixin.run(self)

  def apply(self):
    self.rpm._apply()

