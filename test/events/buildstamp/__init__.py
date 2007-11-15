import unittest

from test import EventTestCase, EventTestRunner

from test.events import make_core_suite

eventid = 'buildstamp'

class DiskbootEventTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, eventid, conf)

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
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
