#
# Copyright (c) 2015
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
import copy

from dtest        import EventTestCase, ModuleTestSuite
from dtest.core   import make_core_suite
from dtest.mixins import ImageModifyMixinTestCase, imm_make_suite

class ProductImageEventTestCase(EventTestCase):
  moduleid = 'product-image'
  eventid  = 'product-image'
  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbuild enabled='false'/>",
    "<config-rpm enabled='false'/>",
    ]

class _ProductImageEventTestCase(ImageModifyMixinTestCase,
                                 ProductImageEventTestCase):
  def __init__(self, os, version, arch, conf=None):
    ProductImageEventTestCase.__init__(self, os, version, arch, conf)
    ImageModifyMixinTestCase.__init__(self)

  def setUp(self):
    ProductImageEventTestCase.setUp(self)
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    ImageModifyMixinTestCase.tearDown(self)
    ProductImageEventTestCase.tearDown(self)

class Test_Installclasses(_ProductImageEventTestCase):
  "at least one installclass is included"
  def runTest(self):
    self.tb.dispatch.execute(until='product-image')

    # copy content; rematch() and fnmatch() are in-place
    self.populate_image_content()
    image_content = copy.copy(self.image_content)
    self.failUnless(image_content.rematch('^installclasses').fnmatch('*.py'))

## TODO - need a test case to check that installclass has the correct
## groups selected - specifically, when comps is enabled

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('product-image')

  suite.addTest(make_core_suite(ProductImageEventTestCase, os, version, arch))
  suite.addTest(imm_make_suite(_ProductImageEventTestCase, os, version, arch, xpath='files'))
  suite.addTest(Test_Installclasses(os, version, arch))

  return suite
