import unittest

from dims import pps

from test      import EventTestCase
from test.core import make_core_suite

class PxebootImagesTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'pxeboot-images', conf)

def make_suite():
  conf = pps.Path(__file__).dirname/'pxeboot-images.conf'
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('pxeboot-images', conf))
  
  return suite
