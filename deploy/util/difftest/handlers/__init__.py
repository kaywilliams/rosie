#
# Copyright (c) 2013
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

class DiffHandler(object):
  def __init__(self):
    self.diffdict = {}

  def difference(self, id=None):
    """Return whether self.diffdict exists (whether there was a difference
    or not).  If id is given, return the difftuple corresponding to that
    id in the diffdict, if present."""
    if id is None:
      return self.diffdict
    else:
      if self.diffdict is not None and self.diffdict.has_key(id):
        return self.diffdict[id]
      else:
        return None

# imported last to avoid circular ref
from config    import ConfigHandler
from input     import InputHandler
from output    import OutputHandler
from variables import VariablesHandler


