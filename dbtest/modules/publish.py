import unittest

from dims import pps

from dbtest.core import make_core_suite

def make_suite():
  confdir = pps.Path(__file__).dirname
  suite = unittest.TestSuite()

  # publish-setup
  suite.addTest(make_core_suite('publish-setup', confdir/'publish-setup.conf'))

  #publish

  return suite
