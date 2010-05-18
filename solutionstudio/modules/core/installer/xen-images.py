#
# Copyright (c) 2010
# Solution Studio Foundation. All rights reserved.
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
from solutionstudio.util import pps

from solutionstudio.event import Event

from solutionstudio.modules.shared import FileDownloadMixin, ImageModifyMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['XenImagesEvent'],
  description = 'includes xen kernel and initrd images',
  group       = 'installer',
)

class XenImagesEvent(Event, ImageModifyMixin, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'xen-images',
      parentid = 'installer',
      version = 2,
      provides = ['vmlinuz-xen', 'initrd-xen', 'treeinfo-checksums'],
      requires = ['anaconda-version', 'buildstamp-file', 'installer-repo'],
      conditionally_requires = ['initrd-image-content', 'remote-baseurl-kickstart-file',
                                'remote-baseurl-ks-path'],
    )

    self.xen_dir = self.SOFTWARE_STORE/'images/xen'

    self.DATA = {
      'config':    ['.'],
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
    if not self.locals.L_FILES['do-xen'][self.basearch]: return

    # fool ImageModifyMixin into using the content of initrd.img for xen's
    # initrd.img as well
    self.cvars['xen-images-content'] = self.cvars['initrd-image-content']

    self.DATA['input'].append(self.cvars['buildstamp-file'])
    if self.cvars['remote-baseurl-kickstart-file']:
      self.DATA['input'].append(self.cvars['remote-baseurl-kickstart-file'])
    self.diff.setup(self.DATA)

    # ImageModifyMixin setup
    self.image_locals = self.locals.L_FILES['xen']['initrd-xen']
    ImageModifyMixin.setup(self)
    self.add_image()

    # FileDownloadMixin setup
    self.file_locals = self.locals.L_FILES['xen']
    FileDownloadMixin.setup(self)

    # add input files from initrd.img
    self.io.add_xpath('path', self.imagedir,
                      id='%s-input-files' % self.name)

  def run(self):
    if not self.locals.L_FILES['do-xen'][self.basearch]: return

    self._download()
    self._modify()

  def apply(self):
    if not self.locals.L_FILES['do-xen'][self.basearch]: return

    self.io.clean_eventcache()

    cvar = self.cvars.setdefault('treeinfo-checksums', set())
    for file in self.SOFTWARE_STORE.findpaths(type=pps.constants.TYPE_NOT_DIR):
      cvar.add((self.SOFTWARE_STORE, file.relpathfrom(self.SOFTWARE_STORE)))

  def verify_image(self):
    # don't print warning if we didn't do anything
    if not self.locals.L_FILES['do-xen'][self.basearch]: return
    ImageModifyMixin.verify_image(self)

  def _generate(self):
    ImageModifyMixin._generate(self)
    self._write_buildstamp()

    # copy remote-baseurl-kickstart
    if self.cvars['remote-baseurl-kickstart-file'] and self.cvars['remote-baseurl-ks-path']:
      self.image.write(self.cvars['remote-baseurl-kickstart-file'], self.cvars['remote-baseurl-ks-path'].dirname)
