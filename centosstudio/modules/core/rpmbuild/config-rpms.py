#
# Copyright (c) 2011
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
from centosstudio.event    import Event, CLASS_META

from centosstudio.modules.shared import (ConfigRpmEvent,
                                         ConfigRpmEventMixin,
                                         make_config_rpm_events,
                                         MkrpmRpmBuildMixin,)

class ConfigRpmsEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'config-rpms',
      parentid = 'rpmbuild',
      ptr = ptr,
      properties = CLASS_META,
      version = '1.00',
      conditionally_comes_after = ['release-rpm'],
      conditionally_comes_before = ['srpmbuild'],
      suppress_run_message = True
    )

# -------- provide module information to dispatcher -------- #
def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['ConfigRpmsEvent'],
    description = 'modules that create RPMs based on user-provided configuration',
  )
  modname = __name__.split('.')[-1]
  new_rpm_events = make_config_rpm_events(ptr, modname, 'config-rpm', 
                                          globals=globals())
  module_info['events'].extend(new_rpm_events)

  return module_info

# -------- init method called by new_rpm_events -------- #
def __init__(self, ptr, *args, **kwargs):
  ConfigRpmEventMixin.__init__(self, ptr, *args, **kwargs)
