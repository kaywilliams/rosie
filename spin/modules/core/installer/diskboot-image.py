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
from StringIO import StringIO

from rendition import pps

from spin.event   import Event

from spin.modules.shared import ImageModifyMixin, BootConfigMixin

P = pps.Path

API_VERSION = 5.0
EVENTS = {'installer': ['DiskbootImageEvent']}

class DiskbootImageEvent(Event, ImageModifyMixin, BootConfigMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'diskboot-image',
      version = 2,
      provides = ['diskboot.img'],
      requires = ['buildstamp-file', 'base-repoid', 'installer-splash',
                  'isolinux-files'],
      conditionally_requires = ['diskboot-image-content', 'web-path', 
                                'boot-args', 'ks-path'],
    )
     
    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']', 'cvars[\'ks-path\']'],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'diskboot.img')
    BootConfigMixin.__init__(self)

  def error(self, e):
    try:
      self._close()
    except:
      pass
    Event.error(self, e)
  
  def setup(self):
    self.DATA['input'].extend([
      self.cvars['installer-splash'],
      self.cvars['isolinux-files']['initrd.img'],
    ])
    
    self.image_locals = self.locals.files['installer']['diskboot.img']
    boot_arg_defaults = ['nousbstorage']
    self.bootconfig._process_method(boot_arg_defaults)
    self.bootconfig._process_ks(boot_arg_defaults)
    self.bootconfig.setup(defaults=boot_arg_defaults)
    ImageModifyMixin.setup(self)
    
  def run(self):
    self._modify()
  
  def _generate(self):
    ImageModifyMixin._generate(self)
    self.image.write(self.cvars['installer-splash'], '/')
    self.image.write(self.cvars['isolinux-files']['initrd.img'], '/')
    
    # hack to modify boot args in syslinux.cfg file
    for file in self.image.list():
      if file.basename == 'syslinux.cfg':
        self.bootconfig.modify(file, cfgfile=file); break
