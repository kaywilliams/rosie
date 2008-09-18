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
from spin.event import Event, CLASS_META

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['VMMetaEvent'],
  description = 'modules that create virtual machine images',
)

class VMMetaEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'vm',
      parentid = 'all',
      properties = CLASS_META,
      provides = ['vms'],
      suppress_run_message = True
    )