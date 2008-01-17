import unittest

from rendition import pps
from rendition.img           import MakeImage
from rendition.xmllib.config import Element
from rendition import si

from spin.splittree import parse_size

from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_core_suite, make_extension_suite
from spintest.mixins import BootConfigMixinTestCase

#------ pkgorder ------#
class PkgorderEventTestCase(EventTestCase):
  moduleid = 'iso'
  eventid  = 'pkgorder'
  _conf = """<iso><set>CD</set></iso>"""

#------ iso ------#
class IsoEventTestCase(EventTestCase):
  moduleid = 'iso'
  eventid  = 'iso'
  _conf = """<iso>
    <boot-config>
      <append-args>ro root=LABEL=/</append-args>
    </boot-config>
    <set>CD</set>
    <set>400 MB</set>
  </iso>"""


class IsoEventBootConfigTestCase(BootConfigMixinTestCase, IsoEventTestCase):
  def __init__(self, basedistro, arch, conf=None):
    IsoEventTestCase.__init__(self, basedistro, arch, conf)
    self.default_args = ['method=cdrom']
    self.image = None
    self.do_defaults = True

  def setUp(self):
    IsoEventTestCase.setUp(self)
    self._append_ks_arg(self.default_args)

  def runTest(self):
    self.tb.dispatch.execute(until='iso')

    for s in self.event.isodir.listdir():
      image = MakeImage(s/'%s-disc1.iso' % self.event.product, 'iso')
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
    <set>101 MiB</set>
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


def make_suite(basedistro, arch):
  suite = ModuleTestSuite('iso')

  # pkgorder
  suite.addTest(make_extension_suite(PkgorderEventTestCase, basedistro, arch))

  # iso
  suite.addTest(make_extension_suite(IsoEventTestCase, basedistro, arch))
  suite.addTest(Test_SizeParser())
  suite.addTest(Test_IsoContent(basedistro, arch))
  suite.addTest(Test_SetsChanged(basedistro, arch))
  suite.addTest(Test_BootArgsDefault(basedistro, arch))
  suite.addTest(Test_BootArgsNoDefault(basedistro, arch))
  suite.addTest(Test_BootArgsMacros(basedistro, arch))
  return suite
