import unittest

from dims import pps

from test.core import make_core_suite

def make_suite():
  conf = pps.Path(__file__).dirname/'ALL.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('ALL', conf))
  
  return suite
