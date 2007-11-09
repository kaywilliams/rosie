import copy
import unittest

from origin import EventTest

from origin.events.core import make_suite as core_make_suite
from origin.events.mixins import ImageModifyMixinTestCase, imm_make_suite

eventid = 'product-image'

class ProductImageEventTest(ImageModifyMixinTestCase):
  def __init__(self, conf):
    ImageModifyMixinTestCase.__init__(self, eventid, conf)
  
  def setUp(self):
    EventTest.setUp(self)
    self.clean_event_md()
  
  
class Test_Installclasses(ProductImageEventTest):
  "at least one installclass is included"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    # copy content; rematch() and fnmatch() are in-place
    self.populate_image_content()
    image_content = copy.copy(self.image_content)
    self.failUnless(image_content.rematch('^installclasses').fnmatch('*.py'))


def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, conf))
  suite.addTest(imm_make_suite(eventid, conf, 'path'))
  suite.addTest(Test_Installclasses(conf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
