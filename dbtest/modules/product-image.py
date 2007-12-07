import copy

from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import ImageModifyMixinTestCase, imm_make_suite

class ProductImageEventTestCase(ImageModifyMixinTestCase):
  def __init__(self, conf=None):
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
  suite = ModuleTestSuite('product-image')

  suite.addTest(make_core_suite('product-image'))
  suite.addTest(imm_make_suite('product-image', xpath='path'))
  suite.addTest(Test_Installclasses())

  return suite
