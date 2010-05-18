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
# a lot of this code is shamelessly ripped from urlgrabber, though most of it
# has been stripped down to a more basic form

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

import xmlrpclib

from rendition.pps import path

# systemid validation
def validate_systemid(systemid):
  "Validate a systemid string to ensure it really is a systemid"
  text = path(systemid).read_text()
  try:
    sysid,_ = xmlrpclib.loads(text)
  except Exception, e:
    raise SystemidInvalidError(systemid, 'error processing systemid: %s' % str(e))
  else:
    sysid = sysid[0]

  # check to make sure all fields are present
  for field in ['system_id', 'fields'] + sysid.get('fields', []):
    if not sysid.has_key(field):
      raise SystemidInvalidError(systemid, 'missing field \'%s\'' % field)

class SystemidInvalidError(StandardError):
  def __str__(self):
    return "Invalid systemid '%s': %s" % (self.args[0], self.args[1])
