import copy
import unittest

from test        import EventTestRunner
from test.core   import make_core_suite
from test.mixins import fdm_make_suite

eventid = 'isolinux'

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(fdm_make_suite(eventid, conf))
  return suite

def main(suite=None):
  import dims.pps
  config = dims.pps.Path(__file__).dirname/'%s.conf' % eventid
  if suite:
    suite.addTest(make_suite(config))
  else:
    EventTestRunner().run(make_suite(config))


if __name__ == '__main__':
  main()
