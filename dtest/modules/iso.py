#
# Copyright (c) 2013
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
import unittest

from deploy.util import pps
from deploy.util.img         import MakeImage
from deploy.util.rxml.config import Element
from deploy.util import si

from deploy.util.splittree import parse_size

from dtest        import EventTestCase, ModuleTestSuite
from dtest.core   import make_core_suite, make_extension_suite
from dtest.mixins import (BootOptionsMixinTestCase, DeployMixinTestCase,
                          dm_make_suite)

#------ pkgorder ------#
class PkgorderEventTestCase(EventTestCase):
  moduleid = 'iso'
  eventid  = 'pkgorder'
  _type = 'system'
  _conf = [
  """<iso><set>CD</set></iso>""",
  ]

#------ iso ------#
class IsoEventTestCase(EventTestCase):
  moduleid = 'iso'
  eventid  = 'iso'
  _type = 'system'
  _conf = ["""
  <iso>
    <set>CD</set>
    <set>500 MB</set>
  </iso>""",
  ]


class IsoEventBootOptionsTestCase(BootOptionsMixinTestCase, IsoEventTestCase):
  def __init__(self, os, version, arch, conf=None):
    IsoEventTestCase.__init__(self, os, version, arch, conf)
    self.image = None
    self.do_defaults = True
    self.default_args = []

  def setUp(self):
    IsoEventTestCase.setUp(self)
    self._append_ks_arg(self.default_args)

  def runTest(self):
    self.tb.dispatch.execute(until='iso')

    for s in self.event.isodir.listdir():
      image = MakeImage(s/'%s-disc1.iso' % self.event.name, 'iso')
      self.testArgs(image, filename='isolinux.cfg', defaults=self.do_defaults)


class Test_SizeParser(unittest.TestCase):
  "splittree.parse_size() checks"
  # this probably technically belongs elsewhere, in another unittest
  def __init__(self):
    unittest.TestCase.__init__(self)
    self.eventid = 'iso'
    self._testMethodDoc = self.__class__.__doc__

  def runTest(self):
    self.failUnlessEqual(parse_size('100'),   si.parse('100'))
    self.failUnlessEqual(parse_size('100b'),  si.parse('100b'))
    self.failUnlessEqual(parse_size('100k'),  si.parse('100k'))
    self.failUnlessEqual(parse_size('100ki'), si.parse('100ki'))
    self.failUnlessEqual(parse_size('100M'),  si.parse('100M'))
    self.failUnlessEqual(parse_size('100Mi'), si.parse('100Mi'))
    self.failUnlessEqual(parse_size('100G'),  si.parse('100G'))
    self.failUnlessEqual(parse_size('100Gi'), si.parse('100Gi'))
    self.failUnlessEqual(parse_size('CD'),    si.parse('640MB'))
    self.failUnlessEqual(parse_size('DVD'),   si.parse('4.7GB'))
    self.failUnlessEqual(parse_size('100 mb'), parse_size('100MB'))

class Test_IsoContent(IsoEventTestCase):
  "iso content matches split tree content"

  def setUp(self):
    self._add_config(
  """<iso>
    <set>CD</set>
    <set>500 MB</set>
  </iso>"""
  )
    IsoEventTestCase.setUp(self)

  def runTest(self):
    self.tb.dispatch.execute(until='iso')

    for s in self.event.config.xpath('set/text()', []):
      splitdir = self.event.splittrees/s
      isodir   = self.event.isodir/s

      for split_tree in splitdir.listdir():
        split_set = set(split_tree.findpaths(mindepth=1).relpathfrom(split_tree))

        image = MakeImage(isodir/'%s.iso' % split_tree.basename, 'iso')
        image.open('r')
        try:
          image_set = set(image.list(relative=True))
        finally:
          image.close()

        self.failIf(not split_set.issubset(image_set), # ignore TRANS.TBL, etc
                    split_set.difference(image_set))

class Test_SetsChanged(IsoEventBootOptionsTestCase):
  "iso sets change"

  def setUp(self):
    self._add_config(
  """<iso>
    <set>640MB</set>
    <set>500 MiB</set>
  </iso>"""
  )
    IsoEventTestCase.setUp(self)

# Note - this test could be made faster if we provided a general method
# for modifing the isolinux configuration, which by default waits 60 seconds
# for the user to manually select the installation type.
class Test_InstallFromIso(DeployMixinTestCase, IsoEventTestCase):
  "installs successfully from iso"

  def setUp(self):
    self._add_config(
  """<iso>
    <set>CD</set>
  </iso>"""
  )
    IsoEventTestCase.setUp(self)

  def __init__(self, os, version, arch, *args, **kwargs):
    IsoEventTestCase.__init__(self, os, version, arch)
    DeployMixinTestCase.__init__(self, os, version, arch, module='publish',
                                 iso=True,
                                 iso_location='iso/CD/%s-disc1.iso' % self.name)

  def setUp(self):
    IsoEventTestCase.setUp(self)
    DeployMixinTestCase.setUp(self)


# run this test after test-install since it alters boot options 
class Test_BootOptionsDefault(IsoEventBootOptionsTestCase):
  "default boot args and config-specified args in isolinux.cfg"

  def setUp(self):
    self._add_config(
  """<iso>
    <set>CD</set>
    <set>500 MB</set>
  </iso>""")

    self._add_config(
    """<publish>
    <boot-options>ro root=LABEL=/</boot-options>
  </publish>""")

    IsoEventBootOptionsTestCase.setUp(self)
    self.do_defaults = True


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('iso')

  # pkgorder
  suite.addTest(make_extension_suite(PkgorderEventTestCase, os, version, arch))

  # iso
  suite.addTest(make_extension_suite(IsoEventTestCase, os, version, arch))
  suite.addTest(Test_SizeParser())
  suite.addTest(Test_IsoContent(os, version, arch))
  suite.addTest(Test_SetsChanged(os, version, arch))
  suite.addTest(Test_InstallFromIso(os, version, arch))
  # dummy test to shutoff vm
  suite.addTest(dm_make_suite(Test_InstallFromIso, os, version, arch, ))
  suite.addTest(Test_BootOptionsDefault(os, version, arch))

  return suite
