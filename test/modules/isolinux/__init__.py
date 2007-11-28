import unittest

from dims import pps

from test.core   import make_core_suite
from test.mixins import fdm_make_suite

def make_suite():
  conf = pps.Path(__file__).dirname/'isolinux.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('isolinux', conf))
  suite.addTest(fdm_make_suite('isolinux', conf))
  
  return suite
