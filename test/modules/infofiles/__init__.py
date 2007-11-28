import unittest

from dims import pps

from test      import EventTestCase
from test.core import make_core_suite

def make_suite():
  confdir = pps.Path(__file__).dirname
  conf_buildstamp = confdir/'buildstamp.conf'
  conf_discinfo = confdir/'discinfo.conf'
  conf_treeinfo = confdir/'treeinfo.conf'
  suite = unittest.TestSuite()

  # buildstamp
  suite.addTest(make_core_suite('buildstamp', conf_buildstamp))

  # discinfo
  suite.addTest(make_core_suite('discinfo', conf_discinfo))

  # treeinfo
  suite.addTest(make_core_suite('treeinfo', conf_treeinfo))

  return suite
