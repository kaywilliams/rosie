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
from systembuildertest        import EventTestCase, ModuleTestSuite
from systembuildertest.core   import make_core_suite
from systembuildertest.mixins import ImageModifyMixinTestCase, imm_make_suite

class UpdatesImageEventTestCase(EventTestCase):
  moduleid = 'updates-image'
  eventid  = 'updates-image'
  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbuild enabled='false'/>",
  ]

class _UpdatesImageEventTestCase(ImageModifyMixinTestCase,
                                 UpdatesImageEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    UpdatesImageEventTestCase.__init__(self, distro, version, arch, conf)
    ImageModifyMixinTestCase.__init__(self)

  def setUp(self):
    UpdatesImageEventTestCase.setUp(self)
    ImageModifyMixinTestCase.setUp(self)

  def tearDown(self):
    ImageModifyMixinTestCase.tearDown(self)
    UpdatesImageEventTestCase.tearDown(self)

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('updates-image')

  suite.addTest(make_core_suite(UpdatesImageEventTestCase, distro, version, arch))
  suite.addTest(imm_make_suite(_UpdatesImageEventTestCase, distro, version, arch, xpath='files'))

  return suite
