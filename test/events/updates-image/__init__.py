import copy
import unittest

from test import EventTest

from test.events.core import make_suite as core_make_suite
from test.events.mixins import ImageModifyMixinTestCase, imm_make_suite

eventid = 'updates-image'

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, conf))
  suite.addTest(imm_make_suite(eventid, conf, 'path'))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname/'%s.conf' % eventid)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
