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
from rendition import shlib

from spin.event import Event

from spin.modules.shared import BootConfigMixin

API_VERSION = 5.0
EVENTS = {'installer': ['BootisoEvent']}

class BootisoEvent(Event, BootConfigMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'bootiso',
      version = 1,
      requires = ['isolinux-files', 'boot-config-file', 'stage2-images'],
      # stage2 is a pseudo requirement, only in later anaconda versions does it apply
      conditionally_requires = ['web-path', 'boot-args'],
    )

    self.bootiso = self.SOFTWARE_STORE/'images/boot.iso'

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'output':    [self.bootiso],
      'variables': ['cvars[\'anaconda-version\']'],
    }

    BootConfigMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.DATA['input'].extend(self.cvars['isolinux-files'].values())
    self.bootconfig.setup(include_method=True, include_ks=True)

  def run(self):
    isodir = self.SOFTWARE_STORE/'images/isopath'
    isolinuxdir = isodir/'isolinux'

    isolinuxdir.mkdirs()
    for fn in self.cvars['isolinux-files'].values():
      if fn.basename == 'isolinux.cfg':
        # copy and modify isolinux.cfg
        self.copy(fn, isolinuxdir)
        self.bootconfig.modify(isolinuxdir/fn.basename)
      else:
        # link other files
        self.link(fn, isolinuxdir)

    # hack - until we have time to do this better
    if self.cvars['anaconda-version'] >= '11.4.0.40':
      imagesdir   = isodir/'images'
      imagesdir.mkdirs()
      self.link(self.cvars['stage2-images']['stage2.img'], imagesdir)

    # apparently mkisofs modifies the mtime of the file it uses as a boot image.
    # to avoid this, we copy the boot image timestamp and overwrite the original
    # when we finish
    ibin = self.cvars['isolinux-files']['isolinux.bin']
    ibin_st = ibin.stat()
    shlib.execute('mkisofs -o %s -b isolinux/isolinux.bin '
                  '-c isolinux/boot.cat -no-emul-boot -boot-load-size 4 '
                  '-boot-info-table -RJTV "%s" %s' \
                  % (self.bootiso, self.product, isodir))
    ibin.utime((ibin_st.st_atime, ibin_st.st_mtime))
    isodir.rm(recursive=True)

  def verify_bootiso_exists(self):
    "boot.iso exists"
    self.verifier.failUnlessExists(self.bootiso)
