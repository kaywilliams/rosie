#
# Copyright (c) 2012
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

import cPickle
import types 

from centosstudio.event import Event

__all__ = ['PickleMixin']


class PickleMixin(Event):
  def __init__(self, *args, **kwargs):
    self.DATA.setdefault('output', [])
    self.pklfile = self.mddir/ '%s.pkl' % self.id
     
  def pickle(self, dict):
    "call in the run function"
    if not type(dict) == types.DictType:
      raise RuntimeError("pickle expecting a dict, got %s") % type(dict)
    fo = self.pklfile.open('wb')
    cPickle.dump(dict, fo, -1)
    self.DATA['output'].append(self.pklfile)
    fo.close()

  def unpickle(self):
    "call in the apply function"
    if self.pklfile.exists():
      fo = self.pklfile.open('rb')
      unpickled = cPickle.load(fo)
      fo.close
    else:
      unpickled = {} 

    return unpickled

  def verify_shelve_file(self):
    self.verifier.failUnlessExists(self.pklfile)
