import unittest

from dims import pps
from dims.img           import MakeImage
from dims.xmllib.config import Element

from dimsbuild.splittree import parse_size

from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.config import make_default_config, add_config_section
from dbtest.core   import make_core_suite, make_extension_suite
from dbtest.mixins import BootConfigMixinTestCase

#------ ISO ------#

#------ pkgorder ------#

#------ iso ------#
class IsoEventTestCase(EventTestCase):
  _conf = \
  """<iso>
    <boot-config>
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
    <set>CD</set>
    <set>400 MB</set>
  </iso>"""
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'iso', conf)


class IsoEventBootConfigTestCase(IsoEventTestCase, BootConfigMixinTestCase):
  def __init__(self, conf=None):
    BootConfigMixinTestCase.__init__(self, 'iso', conf)
    self.default_args = ['method=cdrom']
    self.image = None
    self.do_defaults = True

  def setUp(self):
    BootConfigMixinTestCase.setUp(self)
    self._append_ks_arg(self.default_args)

  def runTest(self):
    self.tb.dispatch.execute(until='iso')

    for s in self.event.isodir.listdir():
      image = MakeImage(s/'%s-disc1.iso' % self.event.product, 'iso')
      self.testArgs(image, filename='isolinux.cfg', defaults=self.do_defaults)


class Test_SizeParser(unittest.TestCase):
  "splittree.parse_size() checks"
  def __init__(self):
    unittest.TestCase.__init__(self)
    self.eventid = 'iso'
    self._testMethodDoc = self.__class__.__doc__

  def runTest(self):
    self.failUnlessEqual(parse_size('100'),    100 * (1024**0))
    self.failUnlessEqual(parse_size('100b'),   100 * (1024**0))
    self.failUnlessEqual(parse_size('100k'),   100 * (1024**1))
    self.failUnlessEqual(parse_size('100kb'),  100 * (1024**1))
    self.failUnlessEqual(parse_size('100M'),   100 * (1024**2))
    self.failUnlessEqual(parse_size('100MB'),  100 * (1024**2))
    self.failUnlessEqual(parse_size('100G'),   100 * (1024**3))
    self.failUnlessEqual(parse_size('100GB'),  100 * (1024**3))
    self.failUnlessEqual(parse_size('CD'),     parse_size('640MB'))
    self.failUnlessEqual(parse_size('DVD'),    parse_size('4.7GB'))
    self.failUnlessEqual(parse_size('100 mb'), parse_size('100MB'))

class Test_IsoContent(IsoEventTestCase):
  "iso content matches split tree content"
  _conf = \
  """<iso>
    <boot-config>
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
    <set>CD</set>
    <set>400 MB</set>
  </iso>"""

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

class Test_SetsChanged(IsoEventBootConfigTestCase):
  "iso sets change"
  _conf = \
  """<iso>
    <boot-config>
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
    <set>640MB</set>
    <set>101 MB</set>
  </iso>"""

class Test_BootArgsDefault(IsoEventBootConfigTestCase):
  "default boot args and config-specified args in isolinux.cfg"
  _conf = \
  """<iso>
    <boot-config use-default="true">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
    <set>CD</set>
    <set>400 MB</set>
  </iso>"""

  def setUp(self):
    IsoEventBootConfigTestCase.setUp(self)
    self.do_defaults = True

class Test_BootArgsNoDefault(IsoEventBootConfigTestCase):
  "default boot args not included"
  _conf = \
  """<iso>
    <boot-config use-default="false">
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
    <set>CD</set>
    <set>400 MB</set>
  </iso>"""

  def setUp(self):
    IsoEventBootConfigTestCase.setUp(self)
    self.do_defaults = False


class Test_BootArgsMacros(IsoEventBootConfigTestCase):
  "macro usage with non-default boot args"
  _conf = \
  """<iso>
    <boot-config use-default="false">
      <append-args>ro root=LABEL=/ %{method} %{ks}</append-args>
    </boot-config>
    <set>CD</set>
    <set>400 MB</set>
  </iso>"""

  def setUp(self):
    IsoEventBootConfigTestCase.setUp(self)
    self.do_defaults = False


def make_suite():
  isoconf = make_default_config('iso')
  add_config_section(isoconf, '<iso><set>CD</set></iso>')

  suite = ModuleTestSuite('iso')

  # ISO
  suite.addTest(make_extension_suite('ISO', isoconf))

  # pkgorder
  suite.addTest(make_extension_suite('pkgorder', isoconf))

  # iso
  suite.addTest(make_extension_suite('iso', isoconf))
  suite.addTest(Test_SizeParser())
  suite.addTest(Test_IsoContent())
  suite.addTest(Test_SetsChanged())
  suite.addTest(Test_BootArgsDefault())
  suite.addTest(Test_BootArgsNoDefault())
  suite.addTest(Test_BootArgsMacros())
  return suite
