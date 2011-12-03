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
from centosstudio.util     import pps
from centosstudio.util.img import MakeImage

from cstest        import EventTestCase, ModuleTestSuite
from cstest.core   import make_core_suite
from cstest.mixins import BootOptionsMixinTestCase

class BootisoEventTestCase(EventTestCase):
  moduleid = 'bootiso'
  eventid  = 'bootiso'

  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbuild enabled='false'/>",
  ]

class _BootisoEventTestCase(BootOptionsMixinTestCase, BootisoEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    EventTestCase.__init__(self, distro, version, arch, conf)
    self.default_args = []
    self.image = None
    self.do_defaults = True

  def setUp(self):
    BootisoEventTestCase.setUp(self)
    self.image = MakeImage(self.event.bootiso, 'iso')
    self._append_method_arg(self.default_args)
    self._append_ks_arg(self.default_args)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='bootiso')

    self.testArgs(self.image, filename='isolinux.cfg', defaults=self.do_defaults)


class Test_BootOptionsDefault(_BootisoEventTestCase):
  "default boot args and config-specified args in isolinux.cfg"
  _conf = _BootisoEventTestCase._conf + [
    "<publish>"
    "  <boot-options>ro root=LABEL=/</boot-options>"
    "</publish>",
  ]

  def setUp(self):
    _BootisoEventTestCase.setUp(self)
    self.do_defaults = True


def make_suite(distro, version, arch):
  suite = ModuleTestSuite('bootiso')

  # bootiso
  suite.addTest(make_core_suite(BootisoEventTestCase, distro, version, arch))
  suite.addTest(Test_BootOptionsDefault(distro, version, arch))

  return suite
