import copy
import unittest

from test               import EventTestRunner
from test.events        import make_core_suite
from test.events.mixins import fdm_make_suite

eventid = 'stage2-images'

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
    runner = EventTestRunner()
    runner.run(make_suite(config))


if __name__ == '__main__':
  main()
