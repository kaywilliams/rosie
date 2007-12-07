import unittest

from dims import pps

from dbtest      import EventTestCase
from dbtest.core import make_core_suite

def make_suite():
  conf = pps.Path(__file__).dirname/'installer.conf'
  suite = unittest.TestSuite()

  suite.addTest(make_core_suite('installer', conf))

  return suite
