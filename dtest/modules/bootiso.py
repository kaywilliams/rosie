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
from deploy.util     import pps
from deploy.util.img import MakeImage

from dtest        import EventTestCase, ModuleTestSuite
from dtest.core   import make_extension_suite
from dtest.mixins import (BootOptionsMixinTestCase, DeployMixinTestCase,
                          dm_make_suite)

class BootisoEventTestCase(EventTestCase):
  moduleid = 'bootiso'
  eventid  = 'bootiso'

  _conf = [
    "<repocreate enabled='false'/>",
    "<rpmbuild enabled='false'/>",
    "<config-rpm enabled='false'/>",
  ]

class _BootisoEventTestCase(BootOptionsMixinTestCase, BootisoEventTestCase):
  def __init__(self, os, version, arch, conf=None):
    EventTestCase.__init__(self, os, version, arch, conf)
    self.default_args = []
    self.image = None
    self.do_defaults = True

  def setUp(self):
    BootisoEventTestCase.setUp(self)
    self._append_method_arg(self.default_args)
    self._append_ks_arg(self.default_args)

  def runTest(self):
    self.tb.dispatch.execute(until='bootiso')

    self.image = MakeImage(self.event.bootiso, 'iso')
    self.testArgs(self.image, filename='isolinux.cfg', defaults=self.do_defaults)


class Test_InstallFromBootiso(DeployMixinTestCase, BootisoEventTestCase):
  "installs from boot.iso"

  _conf = [ ]

  def __init__(self, os, version, arch):
    BootisoEventTestCase.__init__(self, os, version, arch)
    DeployMixinTestCase.__init__(self, os, version, arch, module='publish',
                                 iso=True, iso_location='images/boot.iso')

  def setUp(self):
    BootisoEventTestCase.setUp(self)
    DeployMixinTestCase.setUp(self)

# run this test after test-install since it alters boot options 
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


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('bootiso')

  # bootiso
  suite.addTest(make_extension_suite(BootisoEventTestCase, os, version, arch))
  suite.addTest(Test_InstallFromBootiso(os, version, arch))
  # dummy test to shutoff vm
  suite.addTest(dm_make_suite(Test_InstallFromBootiso, os, version, arch))
  suite.addTest(Test_BootOptionsDefault(os, version, arch))

  return suite
