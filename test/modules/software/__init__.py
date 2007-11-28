import unittest

from dims import pps

from test      import EventTestCase
from test.core import make_core_suite

class SoftwareTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'software', conf)

def make_suite():
  conf = pps.Path(__file__).dirname/'software.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('software', conf))
  
  return suite
