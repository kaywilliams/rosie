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
from spin.locals import *

class LocalsMixin:
  def __init__(self):
    self.locals = LocalsObject(self)

class LocalsObject:
  "Dummy container object for locals information"
  def __init__(self, ptr):
    self.ptr = ptr

  ver = property(lambda self: self.ptr.cvars['anaconda-version'])

  L_FILES             = property(lambda self: L_FILES[self.ver])
  L_BUILDSTAMP_FORMAT = property(lambda self: L_BUILDSTAMP_FORMAT[self.ver])
  L_DISCINFO_FORMAT   = property(lambda self: L_DISCINFO_FORMAT[self.ver])
  L_TREEINFO_FORMAT   = property(lambda self: L_TREEINFO_FORMAT[self.ver])
  L_LOGOS             = property(lambda self: L_LOGOS[self.ver])
  L_INSTALLCLASS      = property(lambda self: L_INSTALLCLASS[self.ver])
  L_RELEASE_HTML      = property(lambda self: L_RELEASE_HTML[self.ver])
  L_GDM_CUSTOM_THEME  = property(lambda self: L_GDM_CUSTOM_THEME[self.ver])
  L_LOGOS_RPM_FILES   = property(lambda self: L_LOGOS_RPM_FILES[self.ver])

# set up locals.L_* variables from local data
#for attr in globals().keys():
#  if attr.startswith('L_'):
#    setattr(LocalsObject, attr, property(lambda self: globals()[attr][self.ver]))

