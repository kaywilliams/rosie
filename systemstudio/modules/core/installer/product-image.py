#
# Copyright (c) 2011
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

from systemstudio.util import pps

from systemstudio.event import Event

from systemstudio.modules.shared import ImageModifyMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ProductImageEvent'],
  description = 'creates a product.img file',
  group       = 'installer',
)

class ProductImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'product-image',
      parentid = 'installer',
      version = 1.04,
      provides = ['product.img', 'treeinfo-checksums', 'os-content'],
      requires = ['anaconda-version', 'buildstamp-file',
                  'installer-repo'],
      conditionally_requires = ['product-image-content'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']',],
      'input':     [],
      'output':    [],
    }

    ImageModifyMixin.__init__(self, 'product.img')

  def error(self, e):
    try:
      self._close()
    except:
      pass
    Event.error(self, e)

  def setup(self):
    self.DATA['input'].append(self.cvars['buildstamp-file'])

    # Diff installclass text, strip leading and trailing whitespace first
    # since this is lost when reading strings back from metadata
    self.installclass = self.locals.L_INSTALLCLASS.strip()
    self.DATA['variables'].append('installclass')

    # ImageModifyMixin setup
    self.image_locals = self.locals.L_FILES['installer']['product.img']
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

    # generate installclasses if none exist
    if len((pps.path(self.image.handler._mount)/'installclasses').findpaths(glob='*.py')) == 0:
      self._generate_installclass()

    # write the buildstamp file to the image
    self._write_buildstamp()

  def _generate_installclass(self):
    self.image.writeflo(StringIO(self.locals.L_INSTALLCLASS),
                        filename='custom.py', dst='installclasses')

