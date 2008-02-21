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
from rendition import pps

from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_core_suite
from spintest.mixins import ImageModifyMixinTestCase, imm_make_suite

class InitrdImageEventTestCase(EventTestCase):
  moduleid = 'initrd-image'
  eventid  = 'initrd-image'

class _InitrdImageEventTestCase(ImageModifyMixinTestCase,
                                InitrdImageEventTestCase):
  def __init__(self, basedistro, arch, conf=None):
    ImageModifyMixinTestCase.__init__(self)
    InitrdImageEventTestCase.__init__(self, basedistro, arch, conf)

  def setUp(self):
    InitrdImageEventTestCase.setUp(self)
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()

  def tearDown(self):
    ImageModifyMixinTestCase.tearDown(self)
    InitrdImageEventTestCase.tearDown(self)


class Test_Kickstart(_InitrdImageEventTestCase):
  "kickstart file included"
  def setUp(self):
    _InitrdImageEventTestCase.setUp(self)
    self.ksfile = self.event.config.getroot().file.abspath().dirname/'ks.cfg'
    self.ksfile.touch()
    self.kspath = pps.Path('/kickstarts/ks1.cfg')
    self.event.cvars['kickstart-file'] = self.ksfile
    self.event.cvars['ks-path'] = self.kspath

  def runTest(self):
    self.tb.dispatch.execute(until='initrd-image')
    self.check_file_in_image(self.kspath.dirname/self.ksfile.basename)

  def tearDown(self):
    _InitrdImageEventTestCase.tearDown(self)
    self.ksfile.remove()


def make_suite(basedistro, arch):
  suite = ModuleTestSuite('initrd-image')

  suite.addTest(make_core_suite(InitrdImageEventTestCase, basedistro, arch))
  suite.addTest(imm_make_suite(_InitrdImageEventTestCase, basedistro, arch, xpath='path'))
  suite.addTest(Test_Kickstart(basedistro, arch))

  return suite
