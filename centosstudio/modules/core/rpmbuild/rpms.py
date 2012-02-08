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

from centosstudio.event import Event

MODULE_INFO = dict(
  api         = 5.0,
  events      = [],
  description = 'module that creates user-defined RPMs',
  group       = 'rpmbuild',
)

class RPMEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)


def __init__(self, ptr, *args, **kwargs):
  Event.__init__(self,
    id = self.__class__.__name__.replace('RpmEvent', '-rpm').lower(),
    parentid = 'rpmbuild',
    ptr = ptr,
    version = 1.00,
    requires = ['rpmbuild-data', ],
    provides = ['repos', 'source-repos', 'comps-object']
  )

  self.DATA = {
    'input':     [],
    'output':    [],
    'variables': [],
  }

def is_enabled(*args, **kwargs):
  if kwargs['ptr'].type == "component": 
    import sys
    for rpm in ['rpm1', 'rpm2', 'rpm3']:
      name = '%sRpmEvent' % rpm.capitalize()
      MODULE_INFO['events'].append(name)
      exec("%s = RPMEvent('%s', (Event,), {'__init__': __init__})" % (name, name)) 
      print rpm
      print getattr(sys.modules[__name__], name)
      print getattr(sys.modules[__name__], name).__dict__
      print MODULE_INFO['events']
    return True
  else: 
    return False
