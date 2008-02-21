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

  files            = property(lambda self: FILES_LOCALS[self.ver])
  buildstamp_fmt   = property(lambda self: BUILDSTAMP_FORMAT_LOCALS[self.ver])
  discinfo_fmt     = property(lambda self: DISCINFO_FORMAT_LOCALS[self.ver])
  logos            = property(lambda self: LOGOS_LOCALS[self.ver])
  installclass     = property(lambda self: INSTALLCLASS_LOCALS[self.ver])
  release_html     = property(lambda self: RELEASE_HTML[self.ver])
  gdm_custom_theme = property(lambda self: GDM_CUSTOM_THEME[self.ver])
  logos_files      = property(lambda self: LOGOS_RPM_FILES_LOCALS[self.ver])
  theme_files      = property(lambda self: THEME_RPM_FILES_LOCALS[self.ver])
