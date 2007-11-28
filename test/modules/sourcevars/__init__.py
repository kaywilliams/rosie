import unittest

from dims import pps

from test      import EventTestCase
from test.core import make_core_suite

class SourceVarsTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'source-vars', conf)

def make_suite():
  conf = pps.Path(__file__).dirname/'source-vars.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('source-vars', conf))
  
  return suite
