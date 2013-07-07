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
from deploy.util import shlib

from deploy.event import Event

from deploy.modules.shared import BootOptionsMixin

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['BootisoEvent'],
    description = 'creates a boot.iso file',
    group       = 'installer',
  )

class BootisoEvent(Event, BootOptionsMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'bootiso',
      parentid = 'installer',
      ptr = ptr,
      version = '1.03',
      requires = ['isolinux-files', 'boot-config-file'],
      provides = ['treeinfo-checksums', 'os-content'],
    )

    self.bootiso = self.OUTPUT_DIR/'images/boot.iso'

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'output':    [self.bootiso],
      'variables': ['cvars[\'anaconda-version\']'],
    }

    BootOptionsMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.DATA['input'].extend(self.cvars['isolinux-files'].values())
    self.bootoptions.setup(include_method=True, include_ks='web')

  def run(self):
    isodir = self.OUTPUT_DIR/'images/isopath'
    isolinuxdir = isodir/'isolinux'

    isolinuxdir.mkdirs()
    for fn in self.cvars['isolinux-files'].values():
      if fn.basename == 'isolinux.cfg':
        # copy and modify isolinux.cfg
        self.copy(fn, isolinuxdir)
        self.bootoptions.modify(isolinuxdir/fn.basename)
      else:
        # link other files
        self.link(fn, isolinuxdir)

    # apparently mkisofs modifies the mtime of the file it uses as a boot image.
    # to avoid this, we copy the boot image timestamp and overwrite the original
    # when we finish
    ibin = self.cvars['isolinux-files']['isolinux.bin']
    ibin_st = ibin.stat()
    shlib.execute('/usr/bin/mkisofs -o %s -b isolinux/isolinux.bin '
                  '-c isolinux/boot.cat -no-emul-boot -boot-load-size 4 '
                  '-boot-info-table -RJTV "%s" %s' \
                  % (self.bootiso, self.name, isodir))
    ibin.utime((ibin_st.st_atime, ibin_st.st_mtime))
    isodir.rm(recursive=True)

  def apply(self):
    self.cvars.setdefault('treeinfo-checksums', set()).add(
      (self.OUTPUT_DIR, 'images/boot.iso'))

  def verify_bootiso_exists(self):
    "boot.iso exists"
    self.verifier.failUnlessExists(self.bootiso)