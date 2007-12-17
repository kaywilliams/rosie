import copy

from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_core_suite
from dbtest.mixins import ImageModifyMixinTestCase, imm_make_suite

class ProductImageEventTestCase(EventTestCase):
  moduleid = 'product-image'
  eventid  = 'product-image'

class _ProductImageEventTestCase(ImageModifyMixinTestCase,
                                 ProductImageEventTestCase):
  def __init__(self, basedistro, conf=None):
    ProductImageEventTestCase.__init__(self, basedistro, conf)
    ImageModifyMixinTestCase.__init__(self)

  def setUp(self):
    ProductImageEventTestCase.setUp(self)
    ImageModifyMixinTestCase.setUp(self)
    self.clean_event_md()

class Test_Installclasses(_ProductImageEventTestCase):
  "at least one installclass is included"
  def runTest(self):
    self.tb.dispatch.execute(until='product-image')

    # copy content; rematch() and fnmatch() are in-place
    self.populate_image_content()
    image_content = copy.copy(self.image_content)
    self.failUnless(image_content.rematch('^installclasses').fnmatch('*.py'))


def make_suite(basedistro):
  suite = ModuleTestSuite('product-image')

  suite.addTest(make_core_suite(ProductImageEventTestCase, basedistro))
  suite.addTest(imm_make_suite(_ProductImageEventTestCase, basedistro, xpath='path'))
  suite.addTest(Test_Installclasses(basedistro))

  return suite
