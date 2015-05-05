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

import shelve as Shelve
import bsddb

from deploy.event import Event
from deploy.errors import DeployEventError

__all__ = ['ShelveMixin']


class ShelveMixin(Event):
  def __init__(self, *args, **kwargs):
    self.shelve_mixin_version = '1.01'
    self.DATA.setdefault('output', set())
    self.DATA.setdefault('variables', set()).add('shelve_mixin_version')
    self.shelvefile = self.mddir/ '%s.shelve' % self.id
     
  def shelve(self, key, value):
    "use this method in the run function to store output"
    d = Shelve.open(self.shelvefile)
    d[key] = value
    if self.shelvefile not in self.DATA['output']:
      self.DATA['output'].add(self.shelvefile)
    d.close()

  def unshelve(self, key, default=None):
    "use this method in the apply function to restore it"
    if self.shelvefile.exists():
      d = Shelve.open(self.shelvefile)
      try:
        if d.has_key(key):
          unshelved = d[key]
        else: 
          unshelved = default
      except bsddb.db.DBPageNotFoundError:
        # db is corrupt, recover gracefully
        self.shelvefile.rm(force=True)
        raise DeployEventError("Deploy detected and repaired a corrupt cache "
                               "file. Please try again.")
      finally:
        d.close
    else:
      unshelved = default

    return unshelved

  def verify_shelve_file(self):
    self.verifier.failUnlessExists(self.shelvefile)
