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
from centosstudio.event   import Event

from centosstudio.modules.shared import ImageModifyMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['InitrdImageEvent'],
  description = 'creates an initrd.img file',
  group       = 'installer',
)

class InitrdImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'initrd-image',
      parentid = 'installer',
      version = '1.01',
      provides = ['isolinux-files', 'os-content'],
      requires = ['anaconda-version', 'buildstamp-file'],
      conditionally_requires = ['initrd-image-content', 'kickstart-file',
                                'ks-path'],
      comes_after = ['isolinux'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [], # to be filled later
      'output':    []  # to be filled later
    }

    ImageModifyMixin.__init__(self, 'initrd.img')

  def error(self, e):
    try:
      self._close()
    except:
      pass
    Event.error(self, e)

  def setup(self):
    self.diff.setup(self.DATA)
    self.DATA['input'].append(self.cvars['buildstamp-file'])
    if self.cvars['kickstart-file']:
      self.DATA['input'].append(self.cvars['kickstart-file'])

    # ImageModifyMixin setup
    self.image_locals = self.locals.L_FILES['isolinux']['initrd.img']
    ImageModifyMixin.setup(self)
    self.add_image()

  def run(self):
    self._modify()

  def apply(self):
    self.io.clean_eventcache()
    self.cvars.setdefault('isolinux-files', {})
    self.cvars['isolinux-files']['initrd.img'] = self.SOFTWARE_STORE/self.image_locals['path']

  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()

    # copy kickstart file
    if self.cvars['kickstart-file'] and self.cvars['ks-path']:
      self.image.write(self.cvars['kickstart-file'], self.cvars['ks-path'].dirname)
