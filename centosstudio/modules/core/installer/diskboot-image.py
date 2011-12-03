#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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
from centosstudio.event import Event

from centosstudio.modules.shared import ImageModifyMixin, BootOptionsMixin

from centosstudio.util import pps
from centosstudio.util import shlib

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['DiskbootImageEvent'],
  description = 'creates a diskboot.img file',
  group       = 'installer',
)

MBR_FILES = [ pps.path('/usr/lib/syslinux/mbr.bin'),
              pps.path('/usr/share/syslinux/mbr.bin'), ]

class DiskbootImageEvent(Event, ImageModifyMixin, BootOptionsMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'diskboot-image',
      version = '1.01',
      parentid = 'installer',
      provides = ['diskboot.img', 'treeinfo-checksums', 'os-content'],
      requires = ['buildstamp-file', 'installer-repo', 'isolinux-files'],
      conditionally_requires = ['diskboot-image-content', 'ks-path', 
                                'installer-splash'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }

    ImageModifyMixin.__init__(self, 'diskboot.img')
    BootOptionsMixin.__init__(self)

  def error(self, e):
    try:
      self._close()
    except:
      pass
    Event.error(self, e)

  def setup(self):
    self.DATA['input'].extend(self.cvars['isolinux-files'].values())

    if ( self.cvars['installer-splash'] is not None and
         self.cvars['installer-splash'].exists() ):
      self.DATA['input'].append(self.cvars['installer-splash'])

    # BootOptionsMixin setup
    self.bootoptions.setup(defaults=['nousbstorage'],
                          include_method=True, include_ks='web')

    # ImageModifyMixin setup
    self.image_locals = self.locals.L_FILES['installer']['diskboot.img']
    ImageModifyMixin.setup(self)
    self.create_image()

  def run(self):
    self._modify()

  def apply(self):
    ImageModifyMixin.apply(self)
    cvar = self.cvars.setdefault('treeinfo-checksums', set())
    for file in self.SOFTWARE_STORE.findpaths(type=pps.constants.TYPE_NOT_DIR):
      cvar.add((self.SOFTWARE_STORE, file.relpathfrom(self.SOFTWARE_STORE)))

  def _generate(self):
    ImageModifyMixin._generate(self)

    if ( self.cvars['installer-splash'] is not None and
         self.cvars['installer-splash'].exists() ):
      self.image.write(self.cvars['installer-splash'], '/')

    for file in self.cvars['isolinux-files'].values():
      self.image.write(file, '/')

    # modify boot args
    isolinuxcfg = self.image.handler._mount/'isolinux.cfg'
    syslinuxcfg = self.image.handler._mount/'syslinux.cfg'
    self.bootoptions.modify(syslinuxcfg, cfgfile=isolinuxcfg)
    isolinuxcfg.remove()
    # remove local lines (essentially grep -v 'local')
    syslinuxcfg.write_lines([ x for x in syslinuxcfg.read_lines()
                              if x.find('local') == -1 ])

    # install syslinux to image
    self.image.close() # syslinux requires image not be mounted
    shlib.execute('syslinux %s' % self.image.imgloc)
    self.image.open()  # ImageModifyMixin expects image to be open when done
