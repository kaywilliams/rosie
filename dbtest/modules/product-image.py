import copy
import unittest

from dims import pps

from dbtest        import EventTestCase
from dbtest.core   import make_core_suite
from dbtest.mixins import ImageModifyMixinTestCase, imm_make_suite

class ProductImageEventTestCase(ImageModifyMixinTestCase):
  def __init__(self, conf):
    ImageModifyMixinTestCase.__init__(self, 'product-image', conf)

  def setUp(self):
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()


class Test_Installclasses(ProductImageEventTestCase):
  "at least one installclass is included"
  def runTest(self):
    self.tb.dispatch.execute(until='product-image')

    # copy content; rematch() and fnmatch() are in-place
    self.populate_image_content()
    image_content = copy.copy(self.image_content)
    self.failUnless(image_content.rematch('^installclasses').fnmatch('*.py'))


def make_suite():
  conf = pps.Path(__file__).dirname/'product-image.conf'
  suite = unittest.TestSuite()

  suite.addTest(make_core_suite('product-image', conf))
  suite.addTest(imm_make_suite('product-image', conf, 'path'))
  suite.addTest(Test_Installclasses(conf))

  return suite
