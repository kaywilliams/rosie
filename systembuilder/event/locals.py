#
# Copyright (c) 2010
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
from systembuilder.locals import *

class LocalsMixin:
  def __init__(self):
    self.locals = LocalsObject(self)

class LocalsObject:
  "Dummy container object for locals information"
  def __init__(self, ptr):
    self.ptr = ptr

  base_name = property(lambda self: self.ptr.cvars['base-info']['fullname'])
  base_ver  = property(lambda self: self.ptr.cvars['base-info']['version'])

  anaconda_ver   = property(lambda self: 'anaconda-%s'   % self.ptr.cvars['anaconda-version'])
  createrepo_ver = property(lambda self: 'createrepo-%s' % self.ptr.cvars['createrepo-version'])

  # anaconda-version based
  L_FILES             = property(lambda self: L_FILES[self.anaconda_ver])
  #L_BUILDINSTALL      = property(lambda self: L_BUILDINSTALL[self.anaconda_ver])
  L_BOOTCFG           = property(lambda self: L_BOOTCFG[self.anaconda_ver])
  L_BUILDSTAMP_FORMAT = property(lambda self: L_BUILDSTAMP_FORMAT[self.anaconda_ver])
  L_DISCINFO_FORMAT   = property(lambda self: L_DISCINFO_FORMAT[self.anaconda_ver])
  L_TREEINFO_FORMAT   = property(lambda self: L_TREEINFO_FORMAT[self.anaconda_ver])
  L_KICKSTART         = property(lambda self: L_KICKSTART[self.anaconda_ver])
  L_LOGOS             = property(lambda self: L_LOGOS[self.anaconda_ver])
  L_INSTALLCLASS      = property(lambda self: L_INSTALLCLASS[self.anaconda_ver])
  L_RELEASE_HTML      = property(lambda self: L_RELEASE_HTML[self.anaconda_ver])
  L_GDM_CUSTOM_THEME  = property(lambda self: L_GDM_CUSTOM_THEME[self.anaconda_ver])

  # createrepo-version based
  L_CREATEREPO        = property(lambda self: L_CREATEREPO[self.createrepo_ver])

  # input distribution and version based
  L_LOGOS_RPM_APPLIANCE_INFO = property(lambda self: L_LOGOS_RPM_APPLIANCE_INFO[self.base_name][self.base_ver])
