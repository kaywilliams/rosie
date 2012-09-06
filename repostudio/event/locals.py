#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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

from repostudio.locals import *

class LocalsMixin:
  def __init__(self):
    self.locals = LocalsObject(self)

class LocalsObject:
  "Dummy container object for locals information"
  def __init__(self, ptr):
    self.ptr = ptr

  base_name = property(lambda self: self.ptr.cvars['base-treeinfo'].get(
                                    'general', 'family'))
  base_ver  = property(lambda self: self.ptr.cvars['base-treeinfo'].get(
                                    'general', 'version'))

  anaconda_ver    = property(lambda self: 'anaconda-%s'   % self.ptr.cvars['anaconda-version'])
  createrepo_ver  = property(lambda self: 'createrepo-%s' % self.ptr.cvars['createrepo-version'])

  # anaconda-version based
  L_FILES             = property(lambda self: L_FILES[self.anaconda_ver])
  #L_BUILDINSTALL      = property(lambda self: L_BUILDINSTALL[self.anaconda_ver])
  L_BOOTCFG           = property(lambda self: L_BOOTCFG[self.anaconda_ver])
  L_BUILDSTAMP_FORMAT = property(lambda self: L_BUILDSTAMP_FORMAT[self.anaconda_ver])
  L_CHECKSUM          = property(lambda self: L_CHECKSUM[self.anaconda_ver])
  L_DISCINFO_FORMAT   = property(lambda self: L_DISCINFO_FORMAT[self.anaconda_ver])
  L_TREEINFO_FORMAT   = property(lambda self: L_TREEINFO_FORMAT[self.anaconda_ver])
  L_LOGOS             = property(lambda self: L_LOGOS[self.anaconda_ver])
  L_INSTALLCLASS      = property(lambda self: L_INSTALLCLASS[self.anaconda_ver])

  # createrepo-version based
  L_CREATEREPO        = property(lambda self: L_CREATEREPO[self.createrepo_ver])

  # base distribution and version based
  L_ANACONDA_VERSION  = property(lambda self: L_ANACONDA_VERSION[self.base_ver])
  L_YUM_PLUGIN        = property(lambda self: L_YUM_PLUGIN[self.base_name][self.base_ver])

  # pykickstart version based
  pykickstart_ver = property(lambda self: 'pykickstart-%s' % self.ptr.cvars['pykickstart-version'])

  def kickstart_get(self):
    adds = L_KICKSTART_ADDS[self.anaconda_ver]
    adds['version']['text'] = adds['version']['text'].replace(
                              '%s', self.base_ver.split('.')[0])
    return adds

  L_KICKSTART_ADDS    = property(kickstart_get)
  L_PYKICKSTART       = property(lambda self: L_PYKICKSTART[self.pykickstart_ver])
