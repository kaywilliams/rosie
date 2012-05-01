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
import re

from centosstudio.event    import Event, CLASS_META
from centosstudio.validate import check_dup_ids

from centosstudio.modules.shared import (ConfigRpmEvent,
                                         ConfigRpmEventMixin,
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

def __init__(self, ptr, *args, **kwargs):
  ConfigRpmEventMixin.__init__(self, ptr, *args, **kwargs)

# -------- provide module information to dispatcher -------- #
def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['ConfigRpmsEvent'],
    description = 'modules that create RPMs based on user-provided configuration',
  )
  modname = __name__.split('.')[-1]
  xpath   = '/*/%s/rpm' % modname

  # ensure unique rpm ids
  check_dup_ids(element = modname,
                config = ptr.definition,
                xpath = '%s/@id' % xpath)

  # create event classes based on user configuration
  for config in ptr.definition.xpath(xpath, []):

    # convert user provided id to a valid class name
    id = config.getxpath('@id')
    name = re.sub('[^0-9a-zA-Z_]', '', id)
    name = '%sConfigRpmEvent' % name.capitalize()

    # get config path
    config_base = '%s[@id="%s"]' % (xpath, id)


    # create new class
    exec """%s = ConfigRpmEvent('%s', 
                         (ConfigRpmEventMixin,), 
                         { 'rpmid'      : '%s',
                           'config_base': '%s',
                           '__init__'   : __init__,
                         }
                        )""" % (name, name, id, config_base) in globals()

    # update module info with new classname
    module_info['events'].append(name)

  return module_info

