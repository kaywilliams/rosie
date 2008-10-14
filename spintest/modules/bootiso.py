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
from rendition     import pps
from rendition.img import MakeImage

from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_core_suite
from spintest.mixins import BootConfigMixinTestCase

class BootisoEventTestCase(EventTestCase):
  moduleid = 'bootiso'
  eventid  = 'bootiso'

  _conf = [
    "<packages enabled='false'/>",
    "<rpmbuild enabled='false'/>",
  ]

class _BootisoEventTestCase(BootConfigMixinTestCase, BootisoEventTestCase):
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


class Test_BootArgsDefault(_BootisoEventTestCase):
  "default boot args and config-specified args in isolinux.cfg"
  _conf = _BootisoEventTestCase._conf + [
    "<bootiso>"
    "  <boot-args use-defaults='true'>ro root=LABEL=/</boot-args>"
    "</bootiso>",
  ]

  def setUp(self):
    _BootisoEventTestCase.setUp(self)
    self.do_defaults = True


class Test_BootArgsNoDefault(_BootisoEventTestCase):
  "default boot args not included"
  _conf = _BootisoEventTestCase._conf + [
    "<bootiso>"
    "  <boot-args use-defaults='false'>ro root=LABEL=/</boot-args>"
    "</bootiso>",
  ]

  def setUp(self):
    _BootisoEventTestCase.setUp(self)
    self.event.config.get('boot-args').attrib['use-defaults'] = 'false'
    self.do_defaults = False


class Test_BootArgsMacros(_BootisoEventTestCase):
  "macro usage with non-default boot args"
  _conf = _BootisoEventTestCase._conf + [
    "<bootiso>"
    "  <boot-args use-defaults='false'>ro root=LABEL=/ %{method} %{ks}</boot-args>"
    "</bootiso>",
  ]

  def setUp(self):
    _BootisoEventTestCase.setUp(self)
    self.do_defaults = False


def make_suite(distro, version, arch):
  suite = ModuleTestSuite('bootiso')

  # bootiso
  suite.addTest(make_core_suite(BootisoEventTestCase, distro, version, arch))
  suite.addTest(Test_BootArgsDefault(distro, version, arch))
  suite.addTest(Test_BootArgsNoDefault(distro, version, arch))
  suite.addTest(Test_BootArgsMacros(distro, version, arch))

  return suite
