import unittest

from dims import pps

from dbtest.core   import make_core_suite
from dbtest.mixins import ImageModifyMixinTestCase, imm_make_suite

def make_suite():
  conf = pps.Path(__file__).dirname/'updates-image.conf'
  suite = unittest.TestSuite()

  suite.addTest(make_core_suite('updates-image', conf))
  suite.addTest(imm_make_suite('updates-image', conf, 'path'))

  return suite
