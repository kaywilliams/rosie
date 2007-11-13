import unittest

from dims.img import MakeImage

from dimsbuild.splittree import parse_size

from test import EventTest

from test.events.core import make_suite as core_make_suite
from test.events.mixins import BootConfigMixinTestCase

eventid = 'iso'

class IsoEventTest(BootConfigMixinTestCase):
  def __init__(self, conf):
    BootConfigMixinTestCase.__init__(self, eventid, conf)
    self.default_args = ['method=cdrom']
    self.image = None

class Test_SizeParser(unittest.TestCase):
  "splittree.parse_size() checks"
  def __init__(self):
    unittest.TestCase.__init__(self)
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

class Test_IsoContent(EventTest):
  "iso content matches split tree content"
  def __init__(self, conf):
    EventTest.__init__(self, eventid, conf)
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
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
      

class Test_BootArgsDefault(IsoEventTest):
  "default boot args and config-specified args in isolinux.cfg"
  def _append_method_arg(self, args):
    args.append('method=cdrom')
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    args = self.default_args
    self._append_method_arg(args)
    self._append_ks_arg(args)
    self._append_config_args(args)
    
    for s in self.event.isodir.listdir():
      if not s.isdir(): continue
      
      image = MakeImage(s/'%s-disc1.iso' % self.event.product, 'iso')
      image.open('r')
      try:
        labels = self.get_boot_args(image.list().fnmatch('isolinux.cfg')[0])
        self.check_boot_args(labels, self.default_args)
        self.check_boot_args(labels, self.event.bootconfig._expand_macros(
          self.event.config.get('boot-config/append-args/text()', '')).split())
      finally:
        image.close()

class Test_BootArgsNoDefault(IsoEventTest):
  "macro usage with non-default boot args"
  def setUp(self):
    IsoEventTest.setUp(self)
    self.clean_event_md()
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    for s in self.event.isodir.listdir():
      if not s.isdir(): continue
      
      image = MakeImage(s/'%s-disc1.iso' % self.event.product, 'iso')
      image.open('r')
      try:
        labels = self.get_boot_args(image.list().fnmatch('isolinux.cfg')[0])
        self.check_boot_args(labels, self.event.bootconfig._expand_macros(
          self.event.config.get('boot-config/append-args/text()', '')).split())
      finally:
        image.close()


def make_suite(confdir):
  dconf = confdir/'default.conf'
  ndconf = confdir/'nodefault.conf'
  
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, dconf))
  suite.addTest(Test_SizeParser())
  suite.addTest(Test_IsoContent(dconf))
  suite.addTest(Test_BootArgsDefault(dconf))
  suite.addTest(Test_BootArgsNoDefault(ndconf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
