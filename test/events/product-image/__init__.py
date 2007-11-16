import copy
import unittest

from test        import EventTestCase, EventTestRunner
from test.core   import make_core_suite
from test.mixins import ImageModifyMixinTestCase, imm_make_suite

eventid = 'product-image'

class ProductImageEventTestCase(ImageModifyMixinTestCase):
  def __init__(self, conf):
    ImageModifyMixinTestCase.__init__(self, eventid, conf)
  
  def setUp(self):
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()
  
  
class Test_Installclasses(ProductImageEventTestCase):
  "at least one installclass is included"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    # copy content; rematch() and fnmatch() are in-place
    self.populate_image_content()
    image_content = copy.copy(self.image_content)
    self.failUnless(image_content.rematch('^installclasses').fnmatch('*.py'))


def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(imm_make_suite(eventid, conf, 'path'))
  suite.addTest(Test_Installclasses(conf))
  return suite

def main(suite=None):
  import dims.pps
  config = dims.pps.Path(__file__).dirname/'%s.conf' % eventid
  if suite:
    suite.addTest(make_suite(config))
  else:
    EventTestRunner().run(make_suite(config))


if __name__ == '__main__':
  main()
