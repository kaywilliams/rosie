import unittest

from dims import pps

from dbtest.core import make_core_suite

#------ init ------#

#------ setup ------#

#------ OS ------#


def make_suite():
  confdir = pps.Path(__file__).dirname
  suite = unittest.TestSuite()

  # init
  suite.addTest(make_core_suite('init', confdir/'init.conf'))

  # setup
  suite.addTest(make_core_suite('setup', confdir/'setup.conf'))

  # OS
  suite.addTest(make_core_suite('OS', confdir/'OS.conf'))

  return suite
