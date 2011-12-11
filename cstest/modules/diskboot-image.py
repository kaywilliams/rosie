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
from centosstudio.util import pps

from cstest        import EventTestCase, ModuleTestSuite
from cstest.core   import make_extension_suite
from cstest.mixins import (ImageModifyMixinTestCase, imm_make_suite,
                             BootOptionsMixinTestCase)

class DiskbootImageEventTestCase(EventTestCase):
  moduleid = 'diskboot-image'
  eventid  = 'diskboot-image'
  _conf = [
    "<repocreate enabled='false'/>",
    "<config-rpm enabled='false'/>",
  ]

class _DiskbootImageEventTestCase(ImageModifyMixinTestCase,
                                  BootOptionsMixinTestCase,
                                  DiskbootImageEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    DiskbootImageEventTestCase.__init__(self, distro, version, arch, conf)
    ImageModifyMixinTestCase.__init__(self)

    self.default_args = ['nousbstorage']
    self.do_defaults = True

  def setUp(self):
    DiskbootImageEventTestCase.setUp(self)
    ImageModifyMixinTestCase.setUp(self)
    self._append_method_arg(self.default_args)
    self._append_ks_arg(self.default_args)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='diskboot-image')
    self.testArgs(self.event.image, filename='syslinux.cfg', defaults=self.do_defaults)

  def tearDown(self):
    ImageModifyMixinTestCase.tearDown(self)
    DiskbootImageEventTestCase.tearDown(self)


class Test_CvarContent(_DiskbootImageEventTestCase):
  "cvars['isolinux-files'] included"
  _conf = _DiskbootImageEventTestCase._conf + [
    "<publish>"
    "   <boot-options>ro root=LABEL=/</boot-options>"
    " </publish>",
  ]

  def runTest(self):
    self.tb.dispatch.execute(until='diskboot-image')

    if self.event.cvars['installer-splash'] is not None:
      self.check_file_in_image(self.event.cvars['installer-splash'].basename)
    self.check_file_in_image(self.event.cvars['isolinux-files']['initrd.img'].basename)

class Test_BootOptionsDefault(_DiskbootImageEventTestCase):
  "default boot args and config-specified args in syslinux.cfg"
  _conf = _DiskbootImageEventTestCase._conf + [
    "<publish>"
    "  <boot-options>ro root=LABEL=/</boot-options>"
    "</publish>",
  ]

  def setUp(self):
    _DiskbootImageEventTestCase.setUp(self)
    self.do_defaults = True

def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('diskboot-image')

  suite.addTest(make_extension_suite(DiskbootImageEventTestCase, distro, version, arch))
  suite.addTest(imm_make_suite(_DiskbootImageEventTestCase, distro, version, arch, xpath='files'))
  suite.addTest(Test_CvarContent(distro, version, arch))
  suite.addTest(Test_BootOptionsDefault(distro, version, arch))

  return suite
