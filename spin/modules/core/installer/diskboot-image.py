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

from spin.event import Event

from spin.modules.shared import ImageModifyMixin, BootConfigMixin

API_VERSION = 5.0
EVENTS = {'installer': ['DiskbootImageEvent']}

class DiskbootImageEvent(Event, ImageModifyMixin, BootConfigMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'diskboot-image',
      version = 1,
      provides = ['diskboot.img'],
      requires = ['buildstamp-file', 'installer-repo', 'isolinux-files'],
      conditionally_requires = ['diskboot-image-content', 'web-path',
                                'boot-args', 'ks-path', 'installer-splash'],
    )

    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
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
    if self.cvars['anaconda-version'] >= '11.4.0.40':
      return # don't make diskboot image after this revision

    self.DATA['input'].append(self.cvars['isolinux-files']['initrd.img'])
    if ( self.cvars['installer-splash'] is not None and
         self.cvars['installer-splash'].exists() ):
      self.DATA['input'].append(self.cvars['installer-splash'])

    self.image_locals = self.locals.L_FILES['installer']['diskboot.img']
    self.bootconfig.setup(defaults=['nousbstorage'], include_method=True, include_ks=True)
    ImageModifyMixin.setup(self)

  def check(self):
    if self.cvars['anaconda-version'] >= '11.4.0.40':
      return False # don't make diskboot image after this revision
    return self.diff.test_diffs()

  def run(self):
    self._modify()

  def verify_image(self):
    "verify image existence."
    if self.cvars['anaconda-version'] >= '11.4.0.40':
      return # don't make diskboot image after this revision
    ImageModifyMixin.verify_image(self)

  def _generate(self):
    if self.cvars['anaconda-version'] >= '11.4.0.40':
      return # don't make diskboot image after this revision

    ImageModifyMixin._generate(self)
    if ( self.cvars['installer-splash'] is not None and
         self.cvars['installer-splash'].exists() ):
      self.image.write(self.cvars['installer-splash'], '/')
    self.image.write(self.cvars['isolinux-files']['initrd.img'], '/')

    # hack to modify boot args in syslinux.cfg file
    for fn in self.image.list():
      if fn.basename == 'syslinux.cfg':
        self.bootconfig.modify(fn, cfgfile=fn); break
