import copy
import unittest

from origin import EventTest

from origin.events.core import make_suite as core_make_suite
from origin.events.mixins import fdm_make_suite

eventid = 'stage2-images'

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, conf))
  suite.addTest(fdm_make_suite(eventid, conf))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
