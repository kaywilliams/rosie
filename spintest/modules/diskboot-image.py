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
from spintest.mixins import (ImageModifyMixinTestCase, imm_make_suite,
                             BootConfigMixinTestCase)

class DiskbootImageEventTestCase(EventTestCase):
  moduleid = 'diskboot-image'
  eventid  = 'diskboot-image'

class _DiskbootImageEventTestCase(ImageModifyMixinTestCase,
                                  BootConfigMixinTestCase,
                                  DiskbootImageEventTestCase):
  def __init__(self, basedistro, arch, conf=None):
    DiskbootImageEventTestCase.__init__(self, basedistro, arch, conf)
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
  _conf = \
  """<diskboot-image>
    <boot-config>
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </diskboot-image>"""

  def runTest(self):
    self.tb.dispatch.execute(until='diskboot-image')

    self.check_file_in_image(self.event.cvars['isolinux-files']['installer-splash'].basename)
    self.check_file_in_image(self.event.cvars['isolinux-files']['initrd.img'].basename)

class Test_BootArgsDefault(_DiskbootImageEventTestCase):
  "default boot args and config-specified args in syslinux.cfg"
  _conf = \
  """<diskboot-image>
    <boot-config use-defaults="true">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </diskboot-image>"""

  def setUp(self):
    _DiskbootImageEventTestCase.setUp(self)
    self.do_defaults = True

class Test_BootArgsNoDefault(_DiskbootImageEventTestCase):
  "default boot args not included"
  _conf = \
  """<diskboot-image>
    <boot-config use-defaults="false">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
  </diskboot-image>"""

  def setUp(self):
    _DiskbootImageEventTestCase.setUp(self)
    self.do_defaults = False

class Test_BootArgsMacros(_DiskbootImageEventTestCase):
  "macro usage with non-default boot args"
  _conf = \
  """<diskboot-image>
    <boot-config use-defaults="false">
      <append-args>ro root=LABEL=/ %{method} %{ks}</append-args>
    </boot-config>
  </diskboot-image>"""

  def setUp(self):
    _DiskbootImageEventTestCase.setUp(self)
    self.do_defaults = False


def make_suite(basedistro, arch):
  suite = ModuleTestSuite('diskboot-image')

  suite.addTest(make_core_suite(DiskbootImageEventTestCase, basedistro, arch))
  suite.addTest(imm_make_suite(_DiskbootImageEventTestCase, basedistro, arch, xpath='path'))
  suite.addTest(Test_CvarContent(basedistro, arch))
  suite.addTest(Test_BootArgsDefault(basedistro, arch))
  suite.addTest(Test_BootArgsNoDefault(basedistro, arch))
  suite.addTest(Test_BootArgsMacros(basedistro, arch))

  return suite
