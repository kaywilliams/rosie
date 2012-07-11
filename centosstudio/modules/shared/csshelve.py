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

import shelve as Shelve

from centosstudio.event import Event

__all__ = ['ShelveMixin']


class ShelveMixin(Event):
  def __init__(self, *args, **kwargs):
    self.shelve_mixin_version = '1.00'
    self.DATA.setdefault('output', [])
    self.DATA.setdefault('variables', []).append('shelve_mixin_version')
    self.shelvefile = self.mddir/ '%s.shelve' % self.id
     
  def shelve(self, key, value):
    "use this method in the run function to store output"
    d = Shelve.open(self.shelvefile)
    d[key] = value
    if self.shelvefile not in self.DATA['output']:
      self.DATA['output'].append(self.shelvefile)
    d.close()

  def unshelve(self, key, default=None):
    "use this method in the apply function to restore it"
    if self.shelvefile.exists():
      d = Shelve.open(self.shelvefile)
      if d.has_key(key):
        unshelved = d[key]
      else: unshelved = default
      d.close
    else:
      unshelved = default

    return unshelved

  def verify_shelve_file(self):
    self.verifier.failUnlessExists(self.shelvefile)
