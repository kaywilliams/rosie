import unittest

from dims import pps

from dbtest      import ModuleTestSuite
from dbtest.core import make_core_suite

#------ init ------#

#------ setup ------#

#------ OS ------#


def make_suite():
  suite = ModuleTestSuite('init')

  # init
  suite.addTest(make_core_suite('init'))

  # setup
  suite.addTest(make_core_suite('setup'))

  # OS
  suite.addTest(make_core_suite('OS'))

  return suite
