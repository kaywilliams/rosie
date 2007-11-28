import unittest

from dims import pps

from test      import EventTestCase
from test.core import make_core_suite

class RpmsTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'rpms', conf)

def make_suite():
  conf = pps.Path(__file__).dirname/'rpms.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('rpms', conf))
  
  return suite
