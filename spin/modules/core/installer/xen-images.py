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
from spin.event   import Event

from spin.modules.shared import FileDownloadMixin, ImageModifyMixin

API_VERSION = 5.0
EVENTS = ['XenImagesEvent']

class XenImagesEvent(Event, ImageModifyMixin, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'xen-images',
      parentid = 'installer',
      version = 2,
      provides = ['vmlinuz-xen', 'initrd-xen'],
      requires = ['anaconda-version', 'buildstamp-file', 'installer-repo'],
      conditionally_requires = ['initrd-image-content', 'kickstart-file', 'ks-path'],
    )

    self.xen_dir = self.SOFTWARE_STORE/'images/xen'

    self.DATA = {
      'config':    ['/distro/initrd-image'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [], # to be filled later
      'output':    []  # to be filled later      
    }

    ImageModifyMixin.__init__(self, 'initrd.img')
    FileDownloadMixin.__init__(self)

  def error(self, e):
    Event.error(self, e)
    try:
      self._close()
    except:
      pass

  def setup(self):
    # fool ImageModifyMixin into using the content of initrd.img for xen's
    # initrd.img as well
    self.cvars['xen-images-content'] = self.cvars['initrd-image-content']

    self.DATA['input'].append(self.cvars['buildstamp-file'])
    if self.cvars['kickstart-file']:
      self.DATA['input'].append(self.cvars['kickstart-file'])
    self.diff.setup(self.DATA)

    self.image_locals = self.locals.L_FILES['xen']['initrd-xen']
    ImageModifyMixin.setup(self)
    self.file_locals = self.locals.L_FILES['xen']
    FileDownloadMixin.setup(self)

    # add input files from initrd.img
    self.io.add_xpath('/distro/initrd-image/path', self.imagedir,
                      id='%s-input-files' % self.name)

  def run(self):
    self._download()
    self._modify()

  def apply(self):
    self.io.clean_eventcache()

  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()

    # copy kickstart
    if self.cvars['kickstart-file'] and self.cvars['ks-path']:
      self.image.write(self.cvars['kickstart-file'], self.cvars['ks-path'].dirname)
