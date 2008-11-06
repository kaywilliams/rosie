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

from spin.event import Event

from spin.modules.shared import ImageModifyMixin

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
      provides = ['product.img', 'treeinfo-checksums'],
      requires = ['anaconda-version', 'buildstamp-file',
                  'installer-repo', 'comps-group-info'],
      conditionally_requires = ['groupfile', 'product-image-content'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']', 'cvars[\'groupfile\']'],
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
    if self.cvars['groupfile'] is not None:
      self.DATA['input'].append(self.cvars['groupfile'])

    # ImageModifyMixin setup
    self.image_locals = self.locals.L_FILES['installer']['product.img']
    ImageModifyMixin.setup(self)
    self.add_or_create_image()

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
    mod = dict(
      groups = self.cvars['user-required-groups'] or ['core'],
      setGroupSelection = self._make_setGroupSelection()
    )

    self.image.writeflo(StringIO(self.locals.L_INSTALLCLASS % mod),
                        filename='custom.py', dst='installclasses')

  def _make_setGroupSelection(self):
    # indentation consistent with files in locals
    lines = ['  def setGroupSelection(self, anaconda):']
    for gi in self.cvars['comps-group-info']:
      lines.append('    anaconda.backend.selectGroup("%s", (%s, %s))' % gi)
    return '\n'.join(lines)
