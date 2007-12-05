import unittest

from dims import pps
from dims.img           import MakeImage
from dims.xmllib.config import Element

from dimsbuild.splittree import parse_size

from dbtest        import EventTestCase
from dbtest.core   import make_core_suite, make_extension_suite
from dbtest.mixins import BootConfigMixinTestCase

#------ ISO ------#

#------ pkgorder ------#

#------ iso ------#
class IsoEventTestCase(BootConfigMixinTestCase):
  def __init__(self, conf):
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

class Test_IsoContent(EventTestCase):
  "iso content matches split tree content"
  def __init__(self, conf):
    EventTestCase.__init__(self, 'iso', conf)

  def runTest(self):
    self.tb.dispatch.execute(until='iso')

    for s in self.event.config.xpath('set/text()', []):
      splitdir = self.event.splittrees/s
      isodir   = self.event.isodir/s

      for split_tree in splitdir.listdir():
        split_set = set(split_tree.findpaths().relpathfrom(split_tree))

        image = MakeImage(isodir/'%s.iso' % split_tree.basename, 'iso')
        image.open('r')
        try:
          image_set = set(image.list(relative=True))
        finally:
          image.close()

        self.failIf(not split_set.issubset(image_set), # ignore TRANS.TBL, etc
                    split_set.difference(image_set))

class Test_SetsChanged(IsoEventTestCase):
  "iso sets change"
  def setUp(self):
    IsoEventTestCase.setUp(self)
    self.event.config.get('set[text()="CD"]').text = '640MB'
    self.event.config.append(Element('set', text='101MB'))

class Test_BootArgsDefault(IsoEventTestCase):
  "default boot args and config-specified args in isolinux.cfg"
  def setUp(self):
    IsoEventTestCase.setUp(self)
    self.event.config.get('boot-config').attrib['use-default'] = 'true'
    self.do_defaults = True

class Test_BootArgsNoDefault(IsoEventTestCase):
  "default boot args not included"
  def setUp(self):
    IsoEventTestCase.setUp(self)
    self.event.config.get('boot-config').attrib['use-default'] = 'false'
    self.do_defaults = False


class Test_BootArgsMacros(IsoEventTestCase):
  "macro usage with non-default boot args"
  def setUp(self):
    IsoEventTestCase.setUp(self)
    self.event.config.get('boot-config').attrib['use-default'] = 'false'
    self.event.config.get('boot-config/append-args').text += ' %{method} %{ks}'
    self.do_defaults = False


def make_suite():
  confdir = pps.Path(__file__).dirname
  conf_ISO = confdir/'ISO.conf'
  conf_iso = confdir/'iso.conf'
  suite = unittest.TestSuite()

  # ISO
  suite.addTest(make_core_suite('ISO', conf_ISO))
  suite.addTest(make_extension_suite('ISO', conf_ISO))

  # pkgorder
  # TODO

  # iso
  suite.addTest(make_core_suite('iso', conf_iso))
  suite.addTest(make_extension_suite('iso', conf_iso))
  suite.addTest(Test_SizeParser())
  suite.addTest(Test_IsoContent(conf_iso))
  suite.addTest(Test_SetsChanged(conf_iso))
  suite.addTest(Test_BootArgsDefault(conf_iso))
  suite.addTest(Test_BootArgsNoDefault(conf_iso))
  suite.addTest(Test_BootArgsMacros(conf_iso))
  return suite
