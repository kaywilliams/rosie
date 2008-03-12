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
from rendition import sortlib
from rendition import xmllib

from spin.event   import Event

from spin.modules.shared import ImageModifyMixin

P = pps.Path


API_VERSION = 5.0
EVENTS = {'installer': ['ProductImageEvent']}

class ProductImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'product-image',
      provides = ['product.img'],
      requires = ['anaconda-version', 'buildstamp-file',
                  'comps-file', 'base-repoid'],
      conditionally_requires = ['product-image-content'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'anaconda-version\']'],
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
    self.image_locals = self.locals.files['installer']['product.img']
    ImageModifyMixin.setup(self)

  def run(self):
    self._modify()

  def _generate(self):
    ImageModifyMixin._generate(self)

    # generate installclasses if none exist
    if len((P(self.image.handler._mount)/'installclasses').findpaths(glob='*.py')) == 0:
      self._generate_installclass()

    # write the buildstamp file to the image
    self._write_buildstamp()

  def _generate_installclass(self):
    comps = xmllib.tree.read(self.cvars['comps-file'])

    installclass = self.locals.installclass % \
      dict( all_groups     = comps.xpath('//group/id/text()'),
            default_groups = comps.xpath('//group[default/text() = "true"]/id/text()') )

    self.image.writeflo(StringIO(installclass),
                        filename='custom.py', dest='installclasses')