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
from deploy.util import pps 
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
      requires = ['isolinux-files', 'stage2-images', 'boot-config-file'],
      provides = ['treeinfo-checksums', 'os-content'],
    )

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'output':    [],
      'variables': ['cvars[\'anaconda-version\']'],
    }

    BootOptionsMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    self.isodir = self.mddir/'build'
    self.bootiso = self.OUTPUT_DIR/'images/boot.iso' # todo: use locals

    for d,f in self.cvars['isolinux-files'].values() + \
               self.cvars['stage2-images'].values():
      self.io.add_fpath(f, self.isodir / pps.path(d).dirname)

    self.bootoptions.setup(include_method='web', include_ks='web')

  def run(self):
    self.io.clean_eventcache(all=True)

    self.bootiso.dirname.mkdirs()

    files = self.io.process_files(callback=self.link_callback, text=None)

    for f in files:
      if f.basename == 'isolinux.cfg':
        self.bootoptions.modify(f)

    # apparently mkisofs modifies the mtime of the file it uses as a boot image.
    # to avoid this, we copy the boot image timestamp and overwrite the original
    # when we finish
    ibin = self.cvars['isolinux-files']['isolinux.bin'][1]
    ibin_st = ibin.stat()
    shlib.execute('/usr/bin/mkisofs -o %s -b isolinux/isolinux.bin '
                  '-c isolinux/boot.cat -no-emul-boot -boot-load-size 4 '
                  '-boot-info-table -RJTV "%s" %s' \
                  % (self.bootiso, self.bootoptions.disc_label, self.isodir))
    shlib.execute('/usr/bin/implantisomd5 --supported-iso "%s"' % self.bootiso)
    ibin.utime((ibin_st.st_atime, ibin_st.st_mtime))
    self.DATA['output'].append(self.bootiso)

  def apply(self):
    self.cvars.setdefault('treeinfo-checksums', set()).add(
      (self.OUTPUT_DIR, 'images/boot.iso'))

  def verify_bootiso_exists(self):
    "boot.iso exists"
    self.verifier.failUnlessExists(self.bootiso)
